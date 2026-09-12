"""
rag_vector.py

Vector-based RAG using ChromaDB for storage and API-based embeddings.
Features: persistent storage, hybrid search (vector + keyword), sentence-aware chunking,
configurable embedding endpoint via EMBEDDING_URL env var.
"""
import json
import os
import hashlib
import re
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Set

from src.constants import CHROMA_DIR
from src.index_walk import prune_index_dirs, is_indexable_file
from pathlib import Path

from src.embedding_lanes import (
    LANE_CUSTOM,
    LANE_FASTEMBED,
    build_embedding_lanes,
    collection_name,
    dedupe_results,
    lane_count,
    migrate_legacy_collection,
    query_lanes,
)

logger = logging.getLogger(__name__)

DEFAULT_FILE_EXTENSIONS: Set[str] = {
    '.txt', '.md', '.py', '.json', '.yaml', '.yml',
    '.csv', '.html', '.css', '.js', '.pdf'
}

# Tool-internal directories that match DEFAULT_FILE_EXTENSIONS but are never
# Directory-walk pruning is single-sourced in src.index_walk so the vector and
# keyword indexers apply the same hidden/junk policy and cannot drift (#5559).

VECTOR_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3

COLLECTION_NAME = "odysseus_rag"


def _generate_doc_id(text: str, owner: str = "") -> str:
    # Owner-scope the id so two owners can index byte-identical chunks
    # without the second one's add early-returning on the first's id and
    # being silently dropped from their owner-filtered search results.
    # Empty owner reproduces the legacy text-only id so the unowned/base
    # index keeps its existing ids and isn't re-churned.
    key = f"{owner}\x00{text}" if owner else text
    return f"doc_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"


def _rewrite_owner_path(value: str, path_map: Dict[str, str], path_prefixes: List[tuple]) -> str:
    if not isinstance(value, str) or not value:
        return value
    abs_value = os.path.abspath(value)
    mapped = path_map.get(abs_value)
    if mapped:
        return mapped
    for old_prefix, new_prefix in path_prefixes:
        old_abs = os.path.abspath(old_prefix)
        new_abs = os.path.abspath(new_prefix)
        if abs_value == old_abs:
            return new_abs
        if abs_value.startswith(old_abs + os.sep):
            return new_abs + abs_value[len(old_abs):]
    return value

def _parse_mrpl_json_records(
    content: str,
    filename: str,
    source_path: str,
    owner: Optional[str] = None,
) -> List[tuple]:
    """
    Convert the MRPL structured JSON corpus into logical RAG documents.

    Each structured record becomes one RAG document instead of being
    split into arbitrary character-based chunks.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse MRPL JSON %s: %s", filename, e)
        return []

    documents = []

    section_labels = {
        "metadata": "MRPL Dataset Metadata",
        "line_lists_and_tag_registry": "Equipment / Tag Registry",
        "pid_graph_connectivity": "P&ID Graph Connectivity",
        "scada_telemetry_historical_blocks": "SCADA Historical Telemetry",
        "sop_and_safety_procedures": "SOP and Safety Procedures",
        "inspection_corrosion_logs": "Inspection and Corrosion Logs",
        "hazop_risk_assessment_worksheets": "HAZOP Risk Assessment",
        "maintenance_work_orders": "Maintenance Work Orders",
        "cause_and_effect_sis_matrix": "Cause and Effect / SIS Matrix",
    }

    identifier_fields = [
        "tag_id",
        "unit_id",
        "unit",
        "unit_name",
        "equipment_tag",
        "equipment_class",
        "connection_id",
        "sop_id",
        "cml_number",
        "worksheet_id",
        "work_order",
        "sap_work_order_number",
        "interlock_tag",
    ]

    for section, records in data.items():

        # metadata is a dictionary, while the other sections
        # are generally lists of records.
        if isinstance(records, dict):
            records = [records]

        if not isinstance(records, list):
            continue

        section_label = section_labels.get(
            section,
            section.replace("_", " ").title()
        )

        for index, record in enumerate(records):

            if not isinstance(record, dict):
                continue

            # Convert the structured record into readable text.
            fields = []

            for key, value in record.items():
                readable_key = key.replace("_", " ").title()

                if isinstance(value, (dict, list)):
                    value_text = json.dumps(
                        value,
                        ensure_ascii=False,
                        separators=(", ", ": "),
                    )
                else:
                    value_text = str(value)

                fields.append(
                    f"{readable_key}: {value_text}"
                )

            document_text = (
                f"MRPL Section: {section_label}\n"
                f"Record Index: {index}\n\n"
                + "\n".join(fields)
            )

            # Metadata stored alongside the embedding.
            metadata = {
                "source": source_path,
                "filename": filename,
                "section": section,
                "section_label": section_label,
                "record_index": index,
                "type": ".json",
            }

            # Preserve important identifiers as Chroma metadata.
            for field in identifier_fields:
                value = record.get(field)

                if value is not None:
                    if isinstance(value, (str, int, float, bool)):
                        metadata[field] = value

            if owner:
                metadata["owner"] = owner

            # Generate a stable record identifier.
            stable_identifier = None

            for field in identifier_fields:
                if record.get(field) is not None:
                    stable_identifier = str(record[field])
                    break

            if stable_identifier:
                record_id = (
                    f"mrpl_{section}_{stable_identifier}"
                )
            else:
                record_id = f"mrpl_{section}_{index}"

            metadata["record_id"] = record_id

            documents.append(
                (document_text, metadata)
            )

    logger.info(
        "Parsed MRPL structured corpus: %d logical records",
        len(documents),
    )

    return documents
class VectorRAG:
    """RAG system using ChromaDB vector storage with hybrid search."""

    def __init__(self, persist_directory: str = CHROMA_DIR):
        self.persist_directory = persist_directory
        self._collection = None
        self._model = None
        self._lanes = []
        self._healthy = False

        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        self._initialize_system()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize_system(self) -> bool:
        try:
            self._lanes = build_embedding_lanes(COLLECTION_NAME)
            if not self._lanes:
                raise RuntimeError("No embedding lanes available")
            self._collection = next(
                (lane.collection for lane in self._lanes if lane.name == LANE_FASTEMBED),
                self._lanes[0].collection,
            )
            self._model = self._lanes[0].client
            migrate_legacy_collection(COLLECTION_NAME, self._lanes)
            logger.info(
                "VectorRAG ready (lanes=%s docs=%s)",
                [lane.name for lane in self._lanes],
                lane_count(self._lanes),
            )
            self._healthy = True
            return True

        except Exception as e:
            logger.error(f"VectorRAG init failed: {e}")
            self._healthy = False
            return False

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if not self._lanes:
            return []
        return np.array(self._lanes[0].encode(texts), dtype=np.float32).tolist()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def healthy(self) -> bool:
        healthy_flag = getattr(self, "_healthy", False)
        if getattr(self, "_lanes", None):
            return healthy_flag and bool(self._lanes)
        return healthy_flag and getattr(self, "_collection", None) is not None

    @property
    def collection(self):
        """Expose the ChromaDB collection for direct access by personal_routes etc."""
        return self._collection

    def _active_collections(self):
        lanes = getattr(self, "_lanes", None)
        if lanes:
            return [(lane.name, lane.collection) for lane in lanes]
        collection = getattr(self, "_collection", None)
        return [("legacy", collection)] if collection is not None else []

    def _collections_for_delete(self):
        collections = []
        seen = set()

        def add(lane_name: str, collection) -> None:
            if collection is None:
                return
            key = getattr(collection, "name", None) or id(collection)
            if key in seen:
                return
            seen.add(key)
            collections.append((lane_name, collection))

        for lane_name, collection in self._active_collections():
            add(lane_name, collection)

        if getattr(self, "_lanes", None):
            try:
                from src.chroma_client import get_chroma_client

                client = get_chroma_client()
                try:
                    add("legacy", client.get_collection(COLLECTION_NAME))
                except Exception:
                    pass
                for lane_name in (LANE_CUSTOM, LANE_FASTEMBED):
                    try:
                        add(lane_name, client.get_collection(collection_name(COLLECTION_NAME, lane_name)))
                    except Exception:
                        pass
            except Exception:
                pass

        return collections

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

    def add_document(self, text: str, metadata: Dict[str, Any]) -> bool:
        if not self.healthy:
            logger.error("Collection not initialized")
            return False
        if not text or not isinstance(text, str):
            return False
        if not metadata or not isinstance(metadata, dict):
            return False

        doc_id = _generate_doc_id(text, metadata.get("owner") or "")
        wrote = False
        for lane in self._lanes:
            try:
                existing = lane.collection.get(ids=[doc_id])
                if existing["ids"]:
                    wrote = True
                    continue
                lane.collection.add(
                    ids=[doc_id],
                    embeddings=lane.encode([text]),
                    documents=[text],
                    metadatas=[metadata],
                )
                wrote = True
            except Exception as e:
                logger.warning("add_document failed in %s lane: %s", lane.name, e)
        return wrote

    def add_documents_batch(self, docs: List[tuple]) -> Dict[str, Any]:
        # If add_document was stubbed/overridden on the instance (e.g. in tests)
        # or lanes are not initialized, delegate through add_document.
        if "add_document" in self.__dict__ or not getattr(self, "_lanes", None):
            added = 0
            failed = 0
            for item in docs:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    t, m = item
                    if self.add_document(t, m):
                        added += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            return {
                "success": (failed == 0 or added > 0),
                "added_count": added,
                "failed_count": failed,
                "message": f"Added {added} documents"
            }

        if not self.healthy:
            return {"success": False, "message": "Collection not initialized"}
        if not docs:
            return {"success": False, "message": "Empty document list"}

        valid = [
            (t, m) for t, m in docs
            if t and isinstance(t, str) and m and isinstance(m, dict)
        ]
        if not valid:
            return {"success": False, "message": "No valid documents"}

        added_ids = set()
        attempted_new = False
        write_failed = False

        for lane in self._lanes:
            all_ids = []
            seen_batch_ids = set()

            for index, (text, meta) in enumerate(valid):
                base_id = _generate_doc_id(text, meta.get("owner") or "")
                doc_id = base_id

                # Prevent duplicate IDs within the same batch.
                # Existing IDs remain unchanged; only duplicate occurrences
                # receive a deterministic suffix.
                if doc_id in seen_batch_ids:
                    doc_id = f"{base_id}_{index}"

                seen_batch_ids.add(doc_id)
                all_ids.append(doc_id)

            try:
                existing = lane.collection.get(ids=all_ids)
                existing_ids = set(existing.get("ids") or [])
            except Exception:
                existing_ids = set()

            new_texts = []
            new_metas = []
            new_ids = []

            for (text, meta), doc_id in zip(valid, all_ids):
                if doc_id not in existing_ids:
                    new_texts.append(text)
                    new_metas.append(meta)
                    new_ids.append(doc_id)

            if new_texts:
                attempted_new = True
                lane_failed = False
                for i in range(0, len(new_texts), 100):
                    batch_texts = new_texts[i:i + 100]
                    batch_ids = new_ids[i:i + 100]
                    batch_metas = new_metas[i:i + 100]
                    try:
                        lane.collection.add(
                            ids=batch_ids,
                            embeddings=lane.encode(batch_texts),
                            documents=batch_texts,
                            metadatas=batch_metas,
                        )
                    except Exception as e:
                        lane_failed = True
                        write_failed = True
                        logger.warning("add_documents_batch failed in %s lane: %s", lane.name, e)
                        break
                if not lane_failed:
                    added_ids.update(new_ids)

        if attempted_new and write_failed and not added_ids:
            return {"success": False, "message": "No embedding lane accepted the batch"}

        return {
            "success": True,
            "added_count": len(added_ids),
            "total_count": len(docs),
            "failed_count": len(docs) - len(valid),
        }

    def rename_owner(
        self,
        old_owner: str,
        new_owner: str,
        *,
        path_map: Optional[Dict[str, str]] = None,
        path_prefixes: Optional[List[tuple]] = None,
    ) -> Dict[str, Any]:
        """Rewrite existing RAG metadata after an auth username rename."""
        if not self.healthy:
            return {"success": False, "updated_count": 0, "message": "Collection not initialized"}

        old_owner = (old_owner or "").strip().lower()
        new_owner = (new_owner or "").strip().lower()
        if not old_owner or not new_owner or old_owner == new_owner:
            return {"success": True, "updated_count": 0, "message": "No owner rename needed"}

        path_map = {os.path.abspath(k): os.path.abspath(v) for k, v in (path_map or {}).items()}
        path_prefixes = path_prefixes or []
        updated_ids = set()
        failed_count = 0

        for lane_name, collection in self._collections_for_delete():
            try:
                results = collection.get(
                    where={"owner": old_owner},
                    include=["metadatas"],
                )
            except Exception as e:
                logger.warning("rename_owner metadata scan failed in %s lane: %s", lane_name, e)
                failed_count += 1
                continue

            ids = results.get("ids") or []
            metadatas = results.get("metadatas") or []
            if not ids:
                continue

            new_metas = []
            selected_ids = []
            for doc_id, meta in zip(ids, metadatas):
                if not isinstance(meta, dict):
                    continue
                next_meta = dict(meta)
                if str(next_meta.get("owner", "")).strip().lower() == old_owner:
                    next_meta["owner"] = new_owner
                for key in ("source", "directory"):
                    next_meta[key] = _rewrite_owner_path(next_meta.get(key), path_map, path_prefixes)
                selected_ids.append(doc_id)
                new_metas.append(next_meta)

            if not selected_ids:
                continue

            try:
                collection.update(ids=selected_ids, metadatas=new_metas)
                updated_ids.update(selected_ids)
            except Exception as e:
                logger.warning("rename_owner metadata update failed in %s lane: %s", lane_name, e)
                failed_count += len(selected_ids)

        success = failed_count == 0
        return {
            "success": success,
            "updated_count": len(updated_ids),
            "failed_count": failed_count,
            "message": f"Updated {len(updated_ids)} RAG chunk(s)",
        }

    # ------------------------------------------------------------------
    # Search — hybrid: vector similarity + keyword overlap
    # ------------------------------------------------------------------

    def search(self, query: str, k: int = 5, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.healthy:
            return []
        if not query or not isinstance(query, str):
            return []
        if lane_count(self._lanes) == 0:
            return []

        try:
            where_filter = {"owner": owner} if owner else None
            query_words = set(query.lower().split())
            stop_words = {"what", "is", "the", "of", "and", "or", "in", "to", "for", "with", "between", "compare", "tell", "me", "about", "show", "vs", "versus"}
            content_query = {w for w in query_words if w not in stop_words} or query_words
            candidates = []

            def _query_and_collect(where_clause):
                found = []
                for lane, results in query_lanes(
                    self._lanes,
                    query,
                    n_results=lambda lane: min(
                        max(k * 15, 80),
                        lane.count(),
                    ),
                    where=where_clause,
                    include=["documents", "metadatas", "distances"],
                    raise_if_all_failed=True,
                ):
                    for idx in range(len(results["ids"][0])):
                        doc_id = results["ids"][0][idx]
                        distance = results["distances"][0][idx]
                        doc_text = results["documents"][0][idx]
                        meta = results["metadatas"][0][idx] or {}

                        vector_sim = 1.0 - distance
                        doc_words = set(doc_text.lower().split())
                        overlap = len(content_query & doc_words)
                        keyword_score = overlap / len(content_query) if content_query else 0.0

                        # Boost direct entity/tag match if present in metadata or text
                        tag_id = (meta.get("tag_id") or "").lower()
                        if tag_id and tag_id in query_words:
                            keyword_score = max(keyword_score, 0.8)

                        unit_id = (meta.get("unit_id") or "").lower()
                        if unit_id and unit_id in query_words:
                            keyword_score = max(keyword_score, 0.7)

                        hybrid_score = (VECTOR_WEIGHT * vector_sim) + (KEYWORD_WEIGHT * keyword_score)

                        found.append({
                            "id": doc_id,
                            "document": doc_text,
                            "metadata": meta,
                            "distance": round(distance, 4),
                            "similarity": round(hybrid_score, 4),
                            "vector_similarity": round(vector_sim, 4),
                            "keyword_score": round(keyword_score, 4),
                            "embedding_lane": lane.name,
                        })
                return found

            candidates = _query_and_collect(where_filter)
            # If owner filter was restrictive and found fewer than k results, fallback to global/unowned
            if owner and len(candidates) < k:
                more = _query_and_collect(None)
                candidates.extend(more)

            # Deduplicate by logical record_id or content hash so identical multi-owner rows don't repeat
            seen_records = set()
            unique_candidates = []
            for c in candidates:
                meta = c.get("metadata") or {}
                rec_key = meta.get("record_id") or hashlib.sha256(c["document"].strip().encode("utf-8")).hexdigest()[:16]
                if rec_key in seen_records:
                    continue
                seen_records.add(rec_key)
                unique_candidates.append(c)

            unique_candidates.sort(key=lambda c: c["similarity"], reverse=True)
            top = unique_candidates[:k]
            logger.info(f"Hybrid search for '{query[:60]}': {len(top)} unique results (from {len(candidates)} candidates)")
            return top

        except Exception as e:
            logger.error(f"search failed: {e}")
            return self._keyword_search_fallback(query, k, owner=owner)

    def _keyword_search_fallback(self, query: str, k: int = 5, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            if not self._active_collections():
                return []

            query_words = query.lower().split()
            scored = []
            for lane_name, collection in self._active_collections():
                if collection.count() == 0:
                    continue
                all_docs = collection.get(include=["documents", "metadatas"])
                if not all_docs["ids"]:
                    continue
                for i, doc in enumerate(all_docs["documents"]):
                    meta = all_docs["metadatas"][i]
                    if owner and meta.get("owner") != owner:
                        continue
                    doc_lower = doc.lower()
                    score = sum(1 for w in query_words if w in doc_lower)
                    if score > 0:
                        scored.append({
                            "id": all_docs["ids"][i],
                            "document": doc,
                            "metadata": meta,
                            "distance": 0,
                            "similarity": score,
                            "search_type": "keyword_fallback",
                            "embedding_lane": lane_name,
                        })

            scored.sort(key=lambda x: x["similarity"], reverse=True)
            return dedupe_results(scored, limit=k)
        except Exception as e:
            logger.error(f"keyword fallback failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def rebuild_index(self) -> bool:
        try:
            from src.chroma_client import get_chroma_client
            client = get_chroma_client()
            try:
                client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass
            for name in (
                collection_name(COLLECTION_NAME, LANE_CUSTOM),
                collection_name(COLLECTION_NAME, LANE_FASTEMBED),
            ):
                try:
                    client.delete_collection(name)
                except Exception:
                    pass
            # Rebuild means empty current lanes. Clear the legacy unsuffixed
            # collection too so startup migration cannot resurrect stale docs.
            self._lanes = build_embedding_lanes(COLLECTION_NAME)
            self._collection = next(
                (lane.collection for lane in self._lanes if lane.name == LANE_FASTEMBED),
                self._lanes[0].collection if self._lanes else None,
            )
            self._healthy = True
            return True
        except Exception as e:
            logger.error(f"rebuild_index failed: {e}")
            self._healthy = False
            return False

    def get_stats(self) -> Dict[str, Any]:
        if not self.healthy:
            return {"error": "Collection not initialized"}
        try:
            return {
                "document_count": lane_count(self._lanes),
                "embedding_model": f"{self._lanes[0].model} @ {self._lanes[0].url}" if self._lanes else "N/A",
                "persist_directory": self.persist_directory,
                "collection_name": COLLECTION_NAME,
                "embedding_lanes": [lane.stats() for lane in self._lanes],
                "healthy": True,
            }
        except Exception as e:
            logger.error(f"get_stats failed: {e}")
            return {"error": str(e), "healthy": False}

    # ------------------------------------------------------------------
    # Directory indexing
    # ------------------------------------------------------------------

    def index_personal_documents(
        self, directory: str, file_extensions: Optional[set] = None, owner: Optional[str] = None
    ) -> Dict[str, Any]:
        if file_extensions is None:
            file_extensions = DEFAULT_FILE_EXTENSIONS

        indexed = 0
        failed = 0
        batch = []
        batch_size = 100

        try:
            for root, dirs, files in os.walk(directory):
                prune_index_dirs(dirs)

                for fname in files:
                    if not is_indexable_file(fname):
                        continue

                    fpath = os.path.join(root, fname)
                    ext = Path(fname).suffix.lower()

                    if ext not in file_extensions:
                        continue

                    try:
                        if ext == '.pdf':
                            from src.personal_docs import extract_pdf_text
                            content = extract_pdf_text(fpath)
                        else:
                            with open(fpath, 'r', encoding='utf-8') as f:
                                content = f.read()

                        if not content or not content.strip():
                            continue

                        meta = {
                            'source': fpath,
                            'filename': fname,
                            'directory': root,
                            'type': ext,
                        }

                        if owner:
                            meta['owner'] = owner

                        # ----------------------------------------------------------
                        # ----------------------------------------------------------
                        # Structured MRPL JSON ingestion
                        # ----------------------------------------------------------
                        if (
                            ext == ".json"
                            and fname.lower() == "mrpl_refinery_300page_corpus.json"
                        ):
                            structured_docs = _parse_mrpl_json_records(
                                content=content,
                                filename=fname,
                                source_path=fpath,
                                owner=owner,
                            )

                            logger.info(
                                "Indexing structured MRPL corpus: %d records",
                                len(structured_docs),
                            )

                            for document_text, document_meta in structured_docs:
                                batch.append(
                                    (document_text, document_meta)
                                )

                                if len(batch) >= batch_size:
                                    result = self.add_documents_batch(batch)

                                    if result.get("success"):
                                        indexed += result.get("added_count", 0)
                                        failed += result.get("failed_count", 0)
                                    else:
                                        failed += len(batch)

                                    logger.info(
                                        "RAG progress: %d records added, %d failed",
                                        indexed,
                                        failed,
                                    )

                                    batch = []

                        else:
                            # ------------------------------------------------------
                            # Existing generic document ingestion
                            # ------------------------------------------------------
                            chunks = self._split_into_chunks(content)

                            logger.info(
                                "Indexing %s: %d chunks",
                                fname,
                                len(chunks),
                            )

                            for i, chunk in enumerate(chunks):
                                batch.append(
                                    (chunk, {**meta, "chunk_id": i})
                                )

                                if len(batch) >= batch_size:
                                    result = self.add_documents_batch(batch)

                                    if result.get("success"):
                                        indexed += result.get("added_count", 0)
                                        failed += result.get("failed_count", 0)
                                    else:
                                        failed += len(batch)

                                    logger.info(
                                        "RAG progress: %d chunks added, %d failed",
                                        indexed,
                                        failed,
                                    )

                                    batch = []

                            if len(batch) >= batch_size:
                                result = self.add_documents_batch(batch)

                                if result.get("success"):
                                    indexed += result.get("added_count", 0)
                                    failed += result.get("failed_count", 0)
                                else:
                                    failed += len(batch)

                                logger.info(
                                    "RAG progress: %d chunks added, %d failed",
                                    indexed,
                                    failed
                                )

                                batch = []

                    except Exception as e:
                        logger.error(f"index {fpath}: {e}")
                        failed += 1

            # Process remaining chunks
            if batch:
                result = self.add_documents_batch(batch)

                if result.get("success"):
                    indexed += result.get("added_count", 0)
                    failed += result.get("failed_count", 0)
                else:
                    failed += len(batch)

            return {
                'success': True,
                'indexed_count': indexed,
                'failed_count': failed,
                'message': f'Indexed {indexed} chunks from {directory}',
            }

        except Exception as e:
            logger.error(f"index_personal_documents {directory}: {e}")
            return {
                'success': False,
                'indexed_count': indexed,
                'failed_count': failed,
                'message': str(e)
            }

    def remove_directory(self, directory: str) -> Dict[str, Any]:
        """Remove all chunks under ``directory`` (recursively), and nothing else.

        Selection is a Python-side path-boundary match on each chunk's stored
        ``source`` full path, NOT a Chroma metadata ``where`` filter. No Chroma
        metadata operator selects a scalar string by path prefix (``$contains``
        targets document content / list membership, not a ``source`` substring),
        and a plain substring would over-delete siblings — removing ``/docs``
        must not touch ``/docs2`` or ``/docs_personal``. We therefore match
        ``source == directory`` or ``source`` startswith ``directory + os.sep``,
        the same boundary rule add_directory uses for exclusions. ``directory``
        is abspath-normalized so it matches the absolute ``source`` that indexing
        always stores, regardless of how the caller passed it in.
        """
        if not self.healthy:
            return {"success": False, "message": "Collection not initialized"}
        directory = os.path.abspath(directory)
        try:
            removed_ids = set()
            for _lane_name, collection in self._collections_for_delete():
                results = collection.get(include=["metadatas"])
                ids = []
                for i, m in enumerate(results["metadatas"]):
                    if not isinstance(m, dict) or not isinstance(m.get("source"), str):
                        continue
                    src = os.path.abspath(m["source"])
                    if (
                        src == directory
                        or src.startswith(directory + os.sep)
                        or m["source"] == directory
                        or m["source"].startswith(directory + os.sep)
                    ):
                        ids.append(results["ids"][i])
                if ids:
                    collection.delete(ids=ids)
                    removed_ids.update(ids)
            if not removed_ids:
                return {"success": True, "removed_count": 0, "message": "No docs found"}

            n = len(removed_ids)
            logger.info(f"Removed {n} chunks from {directory}")
            return {"success": True, "removed_count": n, "message": f"Removed {n} chunks"}
        except Exception as e:
            logger.error(f"remove_directory {directory}: {e}")
            return {"success": False, "message": str(e)}

    def reindex_directory(
        self, directory: str, file_extensions: Optional[set] = None
    ) -> Dict[str, Any]:
        remove_result = self.remove_directory(directory)
        if not remove_result.get("success"):
            return remove_result
        index_result = self.index_personal_documents(directory, file_extensions)
        return {
            "success": index_result.get("success", False),
            "message": (
                f"Re-index for {directory}: removed {remove_result.get('removed_count', 0)}, "
                f"{index_result.get('message', '')}"
            ),
            "removed_count": remove_result.get("removed_count", 0),
            "indexed_count": index_result.get("indexed_count", 0),
            "failed_count": index_result.get("failed_count", 0),
        }

    # ------------------------------------------------------------------
    # Sentence-boundary-aware chunking
    # ------------------------------------------------------------------

    def _split_into_chunks(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> List[str]:
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]

        # Split into sentences first
        sentences = re.split(r'(?<=[.!?])\s+|\n{2,}', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for sentence in sentences:
            sent_len = len(sentence)

            # If a single sentence exceeds chunk_size, split it by character
            if sent_len > chunk_size:
                # Flush current chunk first
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_len = 0

                # Hard-split the long sentence
                for start in range(0, sent_len, chunk_size - overlap):
                    chunks.append(sentence[start:start + chunk_size])
                continue

            if current_len + sent_len + 1 > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Keep last few sentences for overlap
                overlap_sentences: List[str] = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) > overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s) + 1
                current_chunk = overlap_sentences
                current_len = sum(len(s) for s in current_chunk) + max(0, len(current_chunk) - 1)

            current_chunk.append(sentence)
            current_len += sent_len + (1 if current_len > 0 else 0)

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks if chunks else [text]

    # ------------------------------------------------------------------
    # Delete by metadata
    # ------------------------------------------------------------------

    def delete_by_source(self, source: str) -> int:
        """Remove all chunks whose metadata['source'] matches *source*.
        Returns the number of removed chunks."""
        if not self.healthy:
            return 0
        try:
            removed_ids = set()
            for _lane_name, collection in self._collections_for_delete():
                results = collection.get(
                    where={"source": source},
                    include=[],
                )
                ids = results.get("ids", [])
                if ids:
                    collection.delete(ids=ids)
                    removed_ids.update(ids)
            logger.info(f"Deleted {len(removed_ids)} chunks for source={source}")
            return len(removed_ids)
        except Exception as e:
            logger.error(f"delete_by_source failed: {e}")
            return 0

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def retrieve(self, query: str, k: int = 5) -> List[str]:
        return [r['document'] for r in self.search(query, k)]
