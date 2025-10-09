import sys
sys.path.insert(0, 'src')
from src.services.storage import save_data_url_png_to_dir, image_to_data_url
from PIL import Image
import tempfile
import os

# Create test image
img = Image.new('RGB', (100, 100), 'red')
data_url = image_to_data_url(img)

print('Testing both images saving...')
with tempfile.TemporaryDirectory() as tmp:
    orig = save_data_url_png_to_dir(data_url, tmp, 'test_original')
    upsc = save_data_url_png_to_dir(data_url, tmp, 'test_upscaled')
    files = os.listdir(tmp)
    print(f'SUCCESS: {len(files)} files created: {files}')
