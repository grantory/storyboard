import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np
from PIL import Image, ImageOps
from io import BytesIO
import torch
import requests

from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
try:
    # realesr-general-x4v3 uses SRVGG architecture
    from realesrgan.archs.srvgg_arch import SRVGGNetCompact
except Exception:  # fallback path if packaged under basicsr
    from basicsr.archs.srvgg_arch import SRVGGNetCompact

class ImageUpscaler:
    """
    Image upscaling using Real-ESRGAN with the LOW quality model.
    - LOW: realesr-general-x4v3 - ×2 upscale with 0.3 denoise for compressed/pixelated/noisy images
    - Preserves alpha by upscaling RGB via Real-ESRGAN and alpha via Lanczos, then recompositing.
    - Auto-selects FP16 only when CUDA is available.
    """

    def __init__(self, model_name: str = 'realesr-general-x4v3', tile: int = 0, tile_pad: int = 10, model_path: str | None = None):
        self._upsampler: RealESRGANer | None = None
        self._initialized = False
        self._model_name = model_name
        self._tile = tile
        self._tile_pad = tile_pad
        self._model_path = model_path  # None => auto-download/cache

    # -------- Weights management --------
    def _get_weights_dir(self) -> Path:
        """Resolve a writable directory to cache model weights."""
        env_dir = os.environ.get('REAL_ESRGAN_WEIGHTS_DIR')
        if env_dir:
            p = Path(env_dir)
            p.mkdir(parents=True, exist_ok=True)
            return p
        # Default to project-root/weights
        project_root = Path(__file__).resolve().parents[2]
        weights_dir = project_root / 'weights'
        weights_dir.mkdir(parents=True, exist_ok=True)
        return weights_dir

    def _get_model_filename_and_urls(self) -> tuple[str, list[str]]:
        """Return the expected local filename and a list of candidate download URLs for the selected model."""
        if self._model_name == 'realesr-general-x4v3':
            filename = 'realesr-general-x4v3.pth'
            urls = [
                # Official v0.2.5.0 general model
                'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth',
                # Alternative mirror from Real-ESRGAN repository
                'https://raw.githubusercontent.com/xinntao/Real-ESRGAN/master/weights/realesr-general-x4v3.pth',
                # Direct from Real-ESRGAN weights directory
                'https://github.com/xinntao/Real-ESRGAN/raw/master/weights/realesr-general-x4v3.pth',
            ]
            return filename, urls
        raise ValueError(f"Unsupported model: {self._model_name}. Only 'realesr-general-x4v3' is supported.")

    def _is_url(self, path_or_url: str) -> bool:
        return bool(re.match(r'^https?://', str(path_or_url)))

    def _download_with_fallbacks(self, urls: list[str], dest_path: Path) -> str:
        last_err: Exception | None = None
        tmp_path = dest_path.with_suffix(dest_path.suffix + '.part')
        
        print(f"🔍 Attempting to download {dest_path.name} from {len(urls)} sources...")
        
        for i, url in enumerate(urls, 1):
            try:
                print(f"  [{i}/{len(urls)}] Trying: {url}")
                with requests.get(url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(tmp_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    percent = (downloaded / total_size) * 100
                                    print(f"    Progress: {percent:.1f}% ({downloaded}/{total_size} bytes)")
                    
                    # Verify file size
                    if tmp_path.stat().st_size < 1024:  # Less than 1KB is suspicious
                        raise RuntimeError(f"Downloaded file too small: {tmp_path.stat().st_size} bytes")
                    
                    # Move temp to final
                    tmp_path.replace(dest_path)
                    print(f"✅ Successfully downloaded {dest_path.name} ({dest_path.stat().st_size} bytes)")
                    return str(dest_path)
                    
            except Exception as e:
                last_err = e
                print(f"    ❌ Failed: {type(e).__name__}: {e}")
                # Clean temp
                try:
                    if tmp_path.exists():
                        tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
        
        # If all URLs failed, provide helpful error message
        error_msg = f"Failed to download weights to {dest_path.name} from all {len(urls)} sources"
        if last_err:
            error_msg += f"\nLast error: {type(last_err).__name__}: {last_err}"
        error_msg += f"\n\nYou can manually download the weights file and place it in: {dest_path.parent}"
        error_msg += f"\nOr set REAL_ESRGAN_WEIGHTS_DIR environment variable to point to a directory containing the weights."
        
        raise RuntimeError(error_msg)

    def _resolve_model_path(self) -> str:
        """Ensure a local weight file exists and return its local filesystem path."""
        weights_dir = self._get_weights_dir()

        # If explicit path provided by user
        if self._model_path:
            if self._is_url(self._model_path):
                filename = Path(urlparse(self._model_path).path).name or 'model.pth'
                dest = weights_dir / filename
                if not dest.exists() or dest.stat().st_size == 0:
                    return self._download_with_fallbacks([self._model_path], dest)
                return str(dest)
            # Local path
            if Path(self._model_path).exists():
                return str(Path(self._model_path))
            # Provided path does not exist -> try to download treating it as URL
            if self._is_url(str(self._model_path)):
                filename = Path(urlparse(self._model_path).path).name or 'model.pth'
                dest = weights_dir / filename
                return self._download_with_fallbacks([str(self._model_path)], dest)
            raise FileNotFoundError(f"Model path not found: {self._model_path}")

        # Auto-manage based on known model name
        filename, urls = self._get_model_filename_and_urls()
        dest = weights_dir / filename
        
        # Check if already cached
        if dest.exists() and dest.stat().st_size > 1024:  # basic sanity
            print(f"✅ Using cached weights: {dest}")
            return str(dest)
        
        # Check common system locations for existing weights
        common_locations = [
            # Python site-packages weights directory
            Path(torch.__file__).parent.parent / 'weights' / filename,
            # User's home directory
            Path.home() / '.cache' / 'torch' / 'hub' / 'checkpoints' / filename,
            # Current working directory
            Path.cwd() / filename,
        ]
        
        for loc in common_locations:
            if loc.exists() and loc.stat().st_size > 1024:
                print(f"✅ Found existing weights: {loc}")
                # Copy to our cache for future use
                try:
                    import shutil
                    shutil.copy2(loc, dest)
                    print(f"✅ Copied to cache: {dest}")
                    return str(dest)
                except Exception as e:
                    print(f"⚠️  Failed to copy {loc} to cache: {e}")
                    # Use the found location directly
                    return str(loc)
        
        # Download from candidate URLs
        print(f"🔍 No existing weights found, downloading {filename}...")
        return self._download_with_fallbacks(urls, dest)

    def _ensure_initialized(self):
        if self._initialized:
            return

        half = torch.cuda.is_available()  # FP16 only on CUDA

        try:
            # Only support realesr-general-x4v3 model
            if self._model_name == 'realesr-general-x4v3':
                # For realesr-general-x4v3, we use SRVGGNetCompact (v3 general model)
                model_path = self._resolve_model_path()
                model = SRVGGNetCompact(
                    num_in_ch=3,
                    num_out_ch=3,
                    num_feat=64,
                    num_conv=32,
                    upscale=4,
                    act_type='prelu',
                )
                self._upsampler = RealESRGANer(
                    scale=4,  # realesr-general-x4v3 is a 4x model
                    model_path=model_path,
                    model=model,
                    tile=self._tile,
                    tile_pad=self._tile_pad,
                    pre_pad=0,
                    half=half
                )
            else:
                raise ValueError(f"Unsupported model: {self._model_name}. Only 'realesr-general-x4v3' is supported.")
            
            # Validate that the upsampler was properly initialized
            if self._upsampler is None:
                raise RuntimeError(f"RealESRGANer constructor returned None for {self._model_name}")
            
            # Test if the model is actually working by doing a minimal inference
            try:
                test_input = np.zeros((8, 8, 3), dtype=np.uint8)
                with torch.no_grad():
                    # Some versions do not support denoise_strength in enhance()
                    test_output, _ = self._upsampler.enhance(test_input, outscale=1.0)
                if test_output is None:
                    raise RuntimeError("Model test inference returned None")
            except Exception as test_error:
                raise RuntimeError(f"Model test inference failed: {test_error}")

            self._initialized = True
            print(f"✅ Real-ESRGAN upscaler initialized ({self._model_name}, half={half}, tile={self._tile})")
        except Exception as e:
            print(f"❌ Failed to initialize Real-ESRGAN ({self._model_name}): {e}")
            print(f"   Make sure the model file is available and the URL is accessible")
            # Reset state on failure
            self._upsampler = None
            self._initialized = False
            raise

    @staticmethod
    def _pil_to_bgr(pil_img: Image.Image) -> np.ndarray:
        """Convert PIL (any mode) to OpenCV BGR without alpha."""
        if pil_img.mode in ('RGBA', 'LA', 'P'):
            pil_rgb = pil_img.convert('RGBA')
            # Flatten onto white background for processing (we'll preserve alpha separately)
            bg = Image.new('RGB', pil_rgb.size, (255, 255, 255))
            bg.paste(pil_rgb, mask=pil_rgb.split()[-1])
            arr = np.array(bg)
        else:
            arr = np.array(pil_img.convert('RGB'))
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    @staticmethod
    def _resize_alpha(alpha: Image.Image, out_w: int, out_h: int) -> Image.Image:
        """Upscale alpha channel using high-quality filter."""
        return alpha.resize((out_w, out_h), resample=Image.LANCZOS)

    def upscale_image(self, pil_image: Image.Image, outscale: float = 2.0, denoise_strength: float | None = None) -> Image.Image:
        """
        Upscale a PIL image using Real-ESRGAN.

        Args:
            pil_image: Input PIL Image
            outscale:  e.g., 2.0 for 2x upscale
            denoise_strength: 0..1 (if None, uses model default)

        Returns:
            Upscaled PIL Image (RGB or RGBA if original had alpha)
        """
        # Set default denoise strength based on model if not specified
        if denoise_strength is None:
            if self._model_name == 'realesr-general-x4v3':
                denoise_strength = 0.3  # LOW: denoise for compressed/noisy images
        
        self._ensure_initialized()
        assert self._upsampler is not None

        # Normalize orientation
        pil_image = ImageOps.exif_transpose(pil_image)

        # Extract alpha if present (so we can restore it later)
        orig_has_alpha = pil_image.mode in ('RGBA', 'LA') or (pil_image.mode == 'P' and 'transparency' in pil_image.info)
        alpha = None
        if orig_has_alpha:
            pil_rgba = pil_image.convert('RGBA')
            alpha = pil_rgba.split()[-1]  # keep original alpha at input size

        # Convert to BGR for ESRGAN
        img_bgr = self._pil_to_bgr(pil_image)

        t0 = time.time()
        try:
            with torch.no_grad():
                try:
                    out_bgr, _ = self._upsampler.enhance(
                        img_bgr, outscale=float(outscale), denoise_strength=float(denoise_strength)
                    )
                except TypeError:
                    # Fallback for versions that don't support denoise_strength arg
                    out_bgr, _ = self._upsampler.enhance(
                        img_bgr, outscale=float(outscale)
                    )
            elapsed = time.time() - t0

            # Back to PIL RGB
            out_rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
            pil_result = Image.fromarray(out_rgb)

            # Restore alpha if present by upscaling alpha separately and recompositing
            if alpha is not None:
                out_w, out_h = pil_result.size
                alpha_up = self._resize_alpha(alpha, out_w, out_h)
                pil_result = Image.merge('RGBA', (*pil_result.convert('RGB').split(), alpha_up))

            w, h = pil_result.size
            megapixels = (w * h) / 1e6
            print(f"🔍 Upscaled image: {w}x{h} | {megapixels:.2f} MP | {elapsed:.3f}s")

            return pil_result

        except Exception as e:
            print(f"❌ Upscaling failed: {e}")
            raise

    def upscale_from_bytes(self, image_bytes: bytes, outscale: float = 2.0, denoise_strength: float | None = None, output_format: str = "PNG") -> bytes:
        """
        Upscale an image from bytes and return as bytes.

        Args:
            image_bytes:      input image as bytes
            outscale:         scale factor
            denoise_strength: 0..1 (if None, uses model default)
            output_format:    'PNG' or 'WEBP' (PNG preserves alpha)

        Returns:
            bytes of the upscaled image (default PNG)
        """
        pil_image = Image.open(BytesIO(image_bytes))
        upscaled_pil = self.upscale_image(pil_image, outscale, denoise_strength)

        buf = BytesIO()
        save_kwargs = {}
        if output_format.upper() == "WEBP":
            save_kwargs["lossless"] = True
        upscaled_pil.save(buf, format=output_format.upper(), **save_kwargs)
        return buf.getvalue()

# Global instances for reuse (one per model)
_upscaler_instances: dict[str, ImageUpscaler] = {}

def get_upscaler(model_name: str = 'realesr-general-x4v3', tile: int = 0, tile_pad: int = 10, model_path: str | None = None) -> ImageUpscaler:
    """Get or create an upscaler instance for the specified model."""
    global _upscaler_instances
    
    if model_name not in _upscaler_instances:
        _upscaler_instances[model_name] = ImageUpscaler(
            model_name=model_name, 
            tile=tile, 
            tile_pad=tile_pad, 
            model_path=model_path
        )
    
    return _upscaler_instances[model_name]