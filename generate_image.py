"""
Agnes API 图片生成工具
用法：python generate_image.py "<prompt>" [output_filename] [size]

示例：
  python generate_image.py "Wide shot of a modern kitchen with smart appliances" cover.jpg
  python generate_image.py "Close-up of smartphone screen showing hidden features" hero.png 1792x1024

尺寸选项：1024x1024（默认正方形）, 1792x1024（16:9横版封面）, 1024x1792（3:4竖版）, 1536x1024（3:2）
"""
import sys, os, requests
from openai import OpenAI

API_KEY = 'sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui'
BASE_URL = 'https://apihub.agnes-ai.com/v1'
MODEL = 'agnes-image-2.1-flash'

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

prompt = sys.argv[1] if len(sys.argv) > 1 else 'A realistic everyday life scene, natural lighting, clean composition'
output = sys.argv[2] if len(sys.argv) > 2 else None
size = sys.argv[3] if len(sys.argv) > 3 else '1024x1024'

resp = client.images.generate(model=MODEL, prompt=prompt, n=1, size=size)
url = resp.data[0].url
print('IMAGE_URL:', url)

if output:
    r = requests.get(url)
    with open(output, 'wb') as f:
        f.write(r.content)
    print(f'Saved to {output} ({len(r.content)} bytes)')
