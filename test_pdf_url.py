import os
import asyncio
import base64
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_pdf_as_image_url():
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    file_path = os.path.join(os.getcwd(), "exemplos pdf", "380062.pdf")
    
    with open(file_path, "rb") as f:
        pdf_content = f.read()
    
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    data_url = f"data:application/pdf;base64,{pdf_base64}"
    
    print("Calling OpenAI with PDF as image_url...")
    try:
        response = await client.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is in this PDF?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        }
                    ]
                }
            ]
        )
        print("Response:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_pdf_as_image_url())
