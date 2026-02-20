import os
import asyncio
import base64
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_responses_api():
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    file_path = os.path.join(os.getcwd(), "exemplos pdf", "380062.pdf")
    
    with open(file_path, "rb") as f:
        pdf_content = f.read()
    
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    
    print("Testing client.responses.create...")
    try:
        # Check if the attribute exists
        if not hasattr(client, "responses"):
            print("Error: client.responses attribute not found. Checking beta.responses...")
            if not hasattr(client.beta, "responses"):
                print("Error: client.beta.responses not found either.")
                return

        response = await client.responses.create(
            model="gpt-5-nano-2025-08-07",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Extract data from this PDF."},
                        {"type": "input_file", "input_file": {"data": pdf_base64, "format": "pdf"}}
                    ]
                }
            ]
        )
        print("Success!")
        print(response)
    except Exception as e:
        print(f"Failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_responses_api())
