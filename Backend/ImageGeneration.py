"""
Advanced Image Generation System
=================================
Improved version with robust error handling, better async management,
and enhanced reliability.
"""

import asyncio
import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from random import randint
from time import sleep
from dataclasses import dataclass
import traceback

# Third-party imports
from PIL import Image
import requests
from dotenv import get_key

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support"""
    
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
        'RESET': '\033[0m'
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging() -> logging.Logger:
    """Configure logging with colors"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "image_generation.log", encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class ImageGenConfig:
    """Configuration for image generation"""
    api_url: str = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
    data_folder: Path = Path("Data")
    control_file: Path = Path("Frontend") / "Files" / "ImageGeneration.data"
    num_images: int = 3
    poll_interval: float = 1.0
    api_timeout: int = 300  # 5 minutes timeout
    max_retries: int = 3
    retry_delay: float = 2.0
    
    def __post_init__(self):
        """Ensure paths are Path objects"""
        self.data_folder = Path(self.data_folder)
        self.control_file = Path(self.control_file)


# ============================================================================
# API CLIENT
# ============================================================================

class HuggingFaceImageAPI:
    """Hugging Face Image Generation API Client"""
    
    def __init__(self, config: ImageGenConfig):
        self.config = config
        self.api_key = self._load_api_key()
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _load_api_key(self) -> str:
        """Load API key from environment"""
        api_key = get_key('.env', 'HuggingFaceAPIKey')
        
        if not api_key:
            logger.error("❌ HuggingFace API Key not found in .env file!")
            raise ValueError("Missing HuggingFaceAPIKey in .env")
        
        logger.info(f"✓ API Key loaded: {api_key[:10]}...{api_key[-4:]}")
        return api_key
    
    async def generate_image(self, prompt: str, seed: Optional[int] = None) -> Optional[bytes]:
        """Generate a single image"""
        if seed is None:
            seed = randint(0, 1000000)
        
        payload = {
            "inputs": f"{prompt}, quality=4K, sharpness=maximum, Ultra High details, high resolution, seed={seed}",
        }
        
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"API request attempt {attempt + 1}/{self.config.max_retries}")
                
                response = await asyncio.to_thread(
                    self.session.post,
                    self.config.api_url,
                    json=payload,
                    timeout=self.config.api_timeout
                )
                
                # Check response status
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    
                    # Check if we got an image
                    if 'image' in content_type:
                        logger.info(f"✓ Image generated successfully ({len(response.content)} bytes)")
                        return response.content
                    else:
                        logger.warning(f"Unexpected content type: {content_type}")
                        logger.debug(f"Response: {response.text[:200]}")
                
                elif response.status_code == 503:
                    # Model is loading
                    logger.warning("Model is loading, waiting...")
                    try:
                        error_data = response.json()
                        estimated_time = error_data.get('estimated_time', 20)
                        logger.info(f"Estimated wait time: {estimated_time}s")
                        await asyncio.sleep(min(estimated_time + 5, 60))
                    except:
                        await asyncio.sleep(20)
                    continue
                
                else:
                    logger.error(f"API Error {response.status_code}: {response.text[:200]}")
                
                # Retry with delay
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
            
            except requests.Timeout:
                logger.error(f"Request timeout on attempt {attempt + 1}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
            
            except Exception as e:
                logger.error(f"Error generating image: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
        
        logger.error("Failed to generate image after all retries")
        return None
    
    async def generate_multiple_images(self, prompt: str, count: int) -> List[Optional[bytes]]:
        """Generate multiple images concurrently"""
        logger.info(f"Generating {count} images for prompt: '{prompt}'")
        
        tasks = [
            self.generate_image(prompt, seed=randint(0, 1000000))
            for _ in range(count)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and failed generations
        successful_images = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i+1} failed with exception: {result}")
                successful_images.append(None)
            else:
                successful_images.append(result)
        
        success_count = sum(1 for img in successful_images if img is not None)
        logger.info(f"✓ Generated {success_count}/{count} images successfully")
        
        return successful_images


# ============================================================================
# IMAGE MANAGER
# ============================================================================

class ImageManager:
    """Manage image storage and display"""
    
    def __init__(self, config: ImageGenConfig):
        self.config = config
        self.config.data_folder.mkdir(parents=True, exist_ok=True)
    
    def save_images(self, prompt: str, images: List[Optional[bytes]]) -> List[Path]:
        """Save images to disk"""
        safe_prompt = prompt.replace(' ', '_').replace('/', '_').replace('\\', '_')
        saved_paths = []
        
        for i, image_bytes in enumerate(images):
            if image_bytes is None:
                logger.warning(f"Skipping image {i+1} (generation failed)")
                continue
            
            filename = self.config.data_folder / f"{safe_prompt}{i + 1}.jpg"
            
            try:
                # Verify it's actually an image
                img = Image.open(io.BytesIO(image_bytes))
                img.verify()
                
                # Save the image
                with open(filename, "wb") as f:
                    f.write(image_bytes)
                
                logger.info(f"✓ Saved: {filename} ({len(image_bytes)} bytes)")
                saved_paths.append(filename)
            
            except Exception as e:
                logger.error(f"Failed to save {filename}: {e}")
        
        return saved_paths
    
    def display_images(self, image_paths: List[Path], delay: float = 1.0):
        """Display images using PIL"""
        logger.info(f"Opening {len(image_paths)} images...")
        
        for i, image_path in enumerate(image_paths):
            try:
                if not image_path.exists():
                    logger.warning(f"Image not found: {image_path}")
                    continue
                
                img = Image.open(image_path)
                logger.info(f"Opening image {i+1}/{len(image_paths)}: {image_path.name}")
                img.show()
                
                if i < len(image_paths) - 1:  # Don't sleep after last image
                    sleep(delay)
            
            except Exception as e:
                logger.error(f"Failed to open {image_path}: {e}")
    
    def cleanup_old_images(self, prompt: str):
        """Remove old images for the same prompt"""
        safe_prompt = prompt.replace(' ', '_').replace('/', '_').replace('\\', '_')
        pattern = f"{safe_prompt}*.jpg"
        
        for old_file in self.config.data_folder.glob(pattern):
            try:
                old_file.unlink()
                logger.debug(f"Removed old image: {old_file}")
            except Exception as e:
                logger.warning(f"Failed to remove {old_file}: {e}")


# ============================================================================
# CONTROL FILE HANDLER
# ============================================================================

class ControlFileHandler:
    """Handle reading and writing the control file"""
    
    def __init__(self, config: ImageGenConfig):
        self.config = config
        self.config.control_file.parent.mkdir(parents=True, exist_ok=True)
    
    def read(self) -> Optional[Tuple[str, bool]]:
        """Read prompt and status from control file"""
        try:
            if not self.config.control_file.exists():
                logger.warning("Control file doesn't exist, creating default")
                self.write("", False)
                return None
            
            with open(self.config.control_file, 'r', encoding='utf-8') as f:
                data = f.read().strip()
            
            if not data:
                logger.debug("Control file is empty")
                return None
            
            parts = data.split(',')
            
            if len(parts) != 2:
                logger.warning(f"Invalid control file format: '{data}'")
                return None
            
            prompt = parts[0].strip()
            status = parts[1].strip().lower() == 'true'
            
            logger.debug(f"Read control file - Prompt: '{prompt}', Status: {status}")
            return (prompt, status)
        
        except Exception as e:
            logger.error(f"Error reading control file: {e}")
            return None
    
    def write(self, prompt: str, status: bool):
        """Write prompt and status to control file"""
        try:
            status_str = "True" if status else "False"
            data = f"{prompt},{status_str}"
            
            with open(self.config.control_file, 'w', encoding='utf-8') as f:
                f.write(data)
            
            logger.debug(f"Wrote control file: '{data}'")
        
        except Exception as e:
            logger.error(f"Error writing control file: {e}")
    
    def reset(self):
        """Reset control file to default state"""
        self.write("", False)


# ============================================================================
# MAIN IMAGE GENERATOR
# ============================================================================

class ImageGenerator:
    """Main image generation orchestrator"""
    
    def __init__(self, config: Optional[ImageGenConfig] = None):
        self.config = config or ImageGenConfig()
        self.api_client = HuggingFaceImageAPI(self.config)
        self.image_manager = ImageManager(self.config)
        self.control_handler = ControlFileHandler(self.config)
    
    async def generate_and_display(self, prompt: str) -> bool:
        """Generate images for prompt and display them"""
        try:
            logger.info(f"🎨 Starting image generation for: '{prompt}'")
            
            # Optional: cleanup old images
            # self.image_manager.cleanup_old_images(prompt)
            
            # Generate images
            images = await self.api_client.generate_multiple_images(
                prompt, 
                self.config.num_images
            )
            
            # Check if we got any images
            successful_images = [img for img in images if img is not None]
            
            if not successful_images:
                logger.error("❌ No images were generated successfully")
                return False
            
            # Save images
            saved_paths = self.image_manager.save_images(prompt, images)
            
            if not saved_paths:
                logger.error("❌ No images were saved")
                return False
            
            # Display images
            self.image_manager.display_images(saved_paths)
            
            logger.info(f"✓ Image generation complete! Generated {len(saved_paths)} images")
            return True
        
        except Exception as e:
            logger.error(f"Error in generate_and_display: {e}")
            traceback.print_exc()
            return False
    
    def run_polling_loop(self):
        """Main polling loop that watches the control file"""
        logger.info("Starting image generation polling loop...")
        logger.info(f"Watching: {self.config.control_file}")
        logger.info(f"Poll interval: {self.config.poll_interval}s")
        
        iteration = 0
        
        while True:
            try:
                iteration += 1
                
                # Read control file
                result = self.control_handler.read()
                
                if result is None:
                    logger.debug(f"Iteration {iteration}: No valid request")
                    sleep(self.config.poll_interval)
                    continue
                
                prompt, status = result
                
                if not status:
                    logger.debug(f"Iteration {iteration}: Status is False, waiting...")
                    sleep(self.config.poll_interval)
                    continue
                
                if not prompt:
                    logger.warning("Status is True but prompt is empty")
                    self.control_handler.reset()
                    sleep(self.config.poll_interval)
                    continue
                
                # Generate images
                logger.info(f"🎨 Request received: '{prompt}'")
                
                # Run async generation
                success = asyncio.run(self.generate_and_display(prompt))
                
                # Reset control file
                self.control_handler.reset()
                
                if success:
                    logger.info("✓ Request completed successfully")
                else:
                    logger.error("❌ Request failed")
                
                # Exit after processing (as per original behavior)
                logger.info("Exiting after processing request")
                break
            
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                traceback.print_exc()
                sleep(self.config.poll_interval)


# ============================================================================
# ADDITIONAL FIX: Import io module for BytesIO
# ============================================================================
import io


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    try:
        logger.info("=" * 60)
        logger.info("🎨 IMAGE GENERATION SYSTEM STARTING")
        logger.info("=" * 60)
        
        # Create configuration
        config = ImageGenConfig()
        
        # Create and run generator
        generator = ImageGenerator(config)
        generator.run_polling_loop()
    
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
    
    finally:
        logger.info("Image generation system shutdown complete")


if __name__ == "__main__":
    main()
