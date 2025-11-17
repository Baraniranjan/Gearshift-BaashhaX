import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit.plugins import openai
from livekit.agents.llm import ChatContext

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("livekit-openai-fixed")


async def test_chatcontext_methods():
    """Test different ways to create and use ChatContext"""

    logger.info("=== Testing ChatContext Methods ===")

    try:
        llm = openai.LLM()

        # Method 1: Create ChatContext and add messages using append
        logger.info("Method 1: Using append to add messages")
        try:
            chat_ctx = ChatContext()
            chat_ctx.append(role="user", text="Say hello in Hindi")

            logger.info(f"ChatContext messages after append: {chat_ctx.messages}")

            llm_stream = llm.chat(chat_ctx=chat_ctx)

            response = ""
            async for chunk in llm_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response += content
                    logger.info(f"Content: {content}")

            logger.info(f"✅ Method 1 SUCCESS: '{response}'")
            return "Method 1"

        except Exception as e:
            logger.error(f"❌ Method 1 failed: {e}")

        # Method 2: Create ChatContext with messages in constructor
        logger.info("Method 2: Constructor with messages")
        try:
            messages = [{"role": "user", "content": "Say hello in Hindi"}]
            chat_ctx = ChatContext(messages=messages)

            logger.info(f"ChatContext messages: {chat_ctx.messages}")

            llm_stream = llm.chat(chat_ctx=chat_ctx)

            response = ""
            async for chunk in llm_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response += content
                    logger.info(f"Content: {content}")

            logger.info(f"✅ Method 2 SUCCESS: '{response}'")
            return "Method 2"

        except Exception as e:
            logger.error(f"❌ Method 2 failed: {e}")

        # Method 3: Direct messages assignment
        logger.info("Method 3: Direct messages assignment")
        try:
            chat_ctx = ChatContext()
            chat_ctx.messages = [{"role": "user", "content": "Say hello in Hindi"}]

            logger.info(f"ChatContext messages: {chat_ctx.messages}")
            logger.info(f"ChatContext messages length: {len(chat_ctx.messages)}")

            # Check if messages are properly set
            for i, msg in enumerate(chat_ctx.messages):
                logger.info(f"Message {i}: {msg}")

            llm_stream = llm.chat(chat_ctx=chat_ctx)

            response = ""
            async for chunk in llm_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response += content
                    logger.info(f"Content: {content}")

            logger.info(f"✅ Method 3 SUCCESS: '{response}'")
            return "Method 3"

        except Exception as e:
            logger.error(f"❌ Method 3 failed: {e}")

        # Method 4: Check ChatContext attributes and methods
        logger.info("Method 4: Exploring ChatContext")
        try:
            chat_ctx = ChatContext()
            logger.info(f"ChatContext attributes: {[attr for attr in dir(chat_ctx) if not attr.startswith('_')]}")

            # Check if there are other methods to add messages
            if hasattr(chat_ctx, 'add_message'):
                logger.info("Found add_message method")
                chat_ctx.add_message(role="user", content="Say hello in Hindi")
            elif hasattr(chat_ctx, 'add'):
                logger.info("Found add method")
                chat_ctx.add(role="user", content="Say hello in Hindi")
            elif hasattr(chat_ctx, 'append_message'):
                logger.info("Found append_message method")
                chat_ctx.append_message(role="user", content="Say hello in Hindi")

            logger.info(f"ChatContext messages: {chat_ctx.messages}")

        except Exception as e:
            logger.error(f"❌ Method 4 failed: {e}")

        return None

    except Exception as e:
        logger.error(f"ChatContext test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_direct_openai():
    """Test direct OpenAI client as backup"""

    logger.info("=== Testing Direct OpenAI Client ===")

    try:
        import openai as openai_direct

        client = openai_direct.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hello in Hindi"}],
            max_tokens=100
        )

        result = response.choices[0].message.content
        logger.info(f"✅ Direct OpenAI works: '{result}'")
        return True

    except Exception as e:
        logger.error(f"❌ Direct OpenAI failed: {e}")
        return False


async def test_translation_function():
    """Test a working translation function using direct OpenAI"""

    logger.info("=== Testing Translation Function ===")

    try:
        import openai as openai_direct

        client = openai_direct.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        async def translate_text(text: str, target_language: str, prompt: str) -> str:
            """Translation function that works"""
            try:
                loop = asyncio.get_event_loop()

                def sync_translate():
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": text}
                        ],
                        max_tokens=200,
                        temperature=0.3
                    )
                    return response.choices[0].message.content

                result = await loop.run_in_executor(None, sync_translate)
                return result

            except Exception as e:
                logger.error(f"Translation failed: {e}")
                return ""

        # Test translation
        test_text = "Hello, how are you today?"
        prompt = "Translate the following English text to Hindi. Respond with only the translation."

        result = await translate_text(test_text, "hindi", prompt)
        logger.info(f"✅ Translation function works: '{result}'")

        return translate_text

    except Exception as e:
        logger.error(f"❌ Translation function failed: {e}")
        return None


async def main():
    """Run all tests"""

    logger.info("Starting LiveKit OpenAI troubleshooting...")

    # Test 1: Try different ChatContext methods
    working_method = await test_chatcontext_methods()

    if working_method:
        logger.info(f"🎉 Found working LiveKit method: {working_method}")
    else:
        logger.warning("❌ LiveKit OpenAI plugin not working properly")

        # Test 2: Try direct OpenAI as backup
        if await test_direct_openai():
            logger.info("✅ Direct OpenAI works - we can use this as backup")

            # Test 3: Create working translation function
            translate_func = await test_translation_function()
            if translate_func:
                logger.info("🎉 Working translation function created!")
                logger.info("You can use direct OpenAI client instead of LiveKit plugin")
        else:
            logger.error("❌ Even direct OpenAI failed - check your API key")


if __name__ == "__main__":
    asyncio.run(main())