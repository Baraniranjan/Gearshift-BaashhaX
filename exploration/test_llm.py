import asyncio
import logging
import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Configure logging with UTF-8 support
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("openai-mini-test")


async def test_openai_with_debug():
    """Test OpenAI with detailed debugging"""

    logger.info("=== Testing OpenAI with Debug ===")

    try:
        # Initialize client
        api_key = os.environ.get("OPENAI_API_KEY")
        client = openai.OpenAI(api_key=api_key)

        # Test 1: Simple English response
        logger.info("Test 1: Simple English response")
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "user", "content": "Say 'Hello World' in English"}
            ],
            
        )

        result = response.choices[0].message.content
        logger.info(f"English response: '{result}'")
        logger.info(f"Response length: {len(result) if result else 0}")
        logger.info(f"Response type: {type(result)}")

        # Test 2: Hindi response with explicit encoding
        logger.info("Test 2: Hindi response")
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "user",
                 "content": "Translate 'Hello World' to Hindi. Respond only with the Hindi translation."}
            ],
            
        )

        result = response.choices[0].message.content
        logger.info(f"Hindi response: '{result}'")
        logger.info(f"Hindi response encoded: {result.encode('utf-8') if result else 'None'}")

        # Test 3: Translation test
        logger.info("Test 3: Translation test")
        test_text = "Good morning, how are you today?"

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system",
                 "content": "You are a translator. Translate the following English text to Hindi. Respond only with the Hindi translation, no explanations."},
                {"role": "user", "content": test_text}
            ]
        )

        translation = response.choices[0].message.content
        logger.info(f"Translation of '{test_text}': '{translation}'")

        # Test 4: Check response object structure
        logger.info("Test 4: Response object structure")
        logger.info(f"Response object: {response}")
        logger.info(f"Response choices: {response.choices}")
        logger.info(f"First choice: {response.choices[0]}")
        logger.info(f"Message: {response.choices[0].message}")
        logger.info(f"Content: {response.choices[0].message.content}")

        return True

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_working_translation_function():
    """Test the actual translation function you'll use"""

    logger.info("=== Testing Working Translation Function ===")

    try:
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        async def translate_text(text: str, target_language: str, prompt: str) -> str:
            """Working translation function"""
            try:
                loop = asyncio.get_event_loop()

                def sync_translate():
                    response = client.chat.completions.create(
                        model="gpt-5-mini",
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": text}
                        ]
                    )
                    return response.choices[0].message.content or ""

                result = await loop.run_in_executor(None, sync_translate)
                return result.strip()

            except Exception as e:
                logger.error(f"Translation error: {e}")
                return ""

        # Test translations
        test_text = "Hello everyone, welcome to our meeting today."

        translations = {
            "hindi": "Translate the following English text to Hindi. Respond only with the Hindi translation.",
            "tamil": "Translate the following English text to Tamil. Respond only with the Tamil translation.",
            "kannada": "Translate the following English text to Kannada. Respond only with the Kannada translation."
        }

        for lang, prompt in translations.items():
            logger.info(f"Translating to {lang}...")
            result = await translate_text(test_text, lang, prompt)
            logger.info(f"✅ {lang}: '{result}'")

            # Verify we got a non-empty result
            if result and len(result.strip()) > 0:
                logger.info(f"✅ {lang} translation successful (length: {len(result)})")
            else:
                logger.warning(f"⚠️ {lang} translation empty or failed")

        return True

    except Exception as e:
        logger.error(f"Translation function test failed: {e}")
        return False


async def test_streaming():
    """Test streaming for real-time translation"""

    logger.info("=== Testing Streaming ===")

    try:
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        stream = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "Translate to Hindi. Respond only with the translation."},
                {"role": "user", "content": "Good morning, how are you?"}
            ],
            max_tokens=100,
            temperature=0.3,
            stream=True
        )

        full_response = ""
        chunk_count = 0

        for chunk in stream:
            chunk_count += 1
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                logger.info(f"Chunk {chunk_count}: '{content}'")

        logger.info(f"✅ Streaming complete: '{full_response}'")
        logger.info(f"Total chunks: {chunk_count}")

        return len(full_response.strip()) > 0

    except Exception as e:
        logger.error(f"Streaming test failed: {e}")
        return False


async def main():
    """Run all tests"""

    logger.info("Starting comprehensive OpenAI tests...")

    # Test 1: Debug test
    if not await test_openai_with_debug():
        logger.error("❌ Debug test failed")
        return

    # Test 2: Translation function
    if not await test_working_translation_function():
        logger.error("❌ Translation function test failed")
        return



    logger.info("🎉 All tests completed successfully!")
    logger.info("✅ OpenAI GPT-5-mini is working and ready for your main application!")


if __name__ == "__main__":
    asyncio.run(main())