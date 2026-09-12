import sys, os
sys.path.insert(0, os.path.abspath('.'))
import asyncio
from core.session_manager import SessionManager
from src.constants import SESSIONS_FILE, BASE_DIR
from src.rag_singleton import get_rag_manager
from src.app_initializer import initialize_managers
from routes.chat_helpers import build_chat_context

async def test():
    rag = get_rag_manager()
    comp = initialize_managers(BASE_DIR, rag)
    sm = comp['session_manager']
    sess = sm.get_session('test-sess-1')
    if not sess:
        sess = sm.create_session(
            session_id='test-sess-1',
            endpoint_url='http://localhost:11434/v1',
            name='Test MRPL',
            model='qwen3.5:4b'
        )
    class MockState:
        user = 'admin'
    class MockRequest:
        state = MockState()
        headers = {}
        cookies = {}

    ctx = await build_chat_context(
        sess=sess,
        request=MockRequest(),
        chat_handler=comp['chat_handler'],
        chat_processor=comp['chat_processor'],
        message='What is the metallurgy and piping spec for equipment 011-C-101 in CDU Phase III?',
        session_id=sess.id,
    )
    print('RAG sources count:', len(ctx.rag_sources))
    for s in ctx.rag_sources:
        print('  Source:', s)
    print('Messages count:', len(ctx.messages))
    for m in ctx.messages:
        role = m.get('role')
        content = m.get('content', '')
        print(f'=== Role: {role} ===')
        print(content[:300])
        print('...\n')

    from src.llm_core import llm_call_async
    print('Calling LLM with model:', sess.model)
    reply = await llm_call_async(
        url=sess.endpoint_url,
        model=sess.model,
        messages=ctx.messages,
    )
    print('=== LLM Reply ===')
    print(reply)

if __name__ == '__main__':
    asyncio.run(test())
