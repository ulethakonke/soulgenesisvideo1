import cv2
import numpy as np
import gc
import tempfile
import os
from pathlib import Path

def compress_video_direct(input_path, output_path, quality_preset="medium", target_fps=20, max_resolution=480):
    """
    Direct MP4 to compressed MP4 conversion - no intermediate files
    """
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {input_path}")
    
    try:
        # Get video properties
        original_fps = cap.get(cv2.CAP_PROP_FPS) or 24
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"Original: {width}x{height}, {original_fps:.1f} FPS, {total_frames} frames")
        
        # Quality presets - aggressive compression settings
        quality_settings = {
            "ultra": {
                "crf": 35,           # Higher = more compression
                "preset": "ultrafast",
                "scale_factor": 0.4,
                "fps_reduction": 0.6
            },
            "high": {
                "crf": 30,
                "preset": "fast", 
                "scale_factor": 0.5,
                "fps_reduction": 0.7
            },
            "medium": {
                "crf": 28,
                "preset": "medium",
                "scale_factor": 0.6,
                "fps_reduction": 0.8
            },
            "low": {
                "crf": 25,
                "preset": "slow",
                "scale_factor": 0.7,
                "fps_reduction": 0.9
            }
        }
        
        settings = quality_settings[quality_preset]
        
        # Calculate output dimensions
        scale = settings["scale_factor"]
        if max(width, height) > max_resolution:
            if width > height:
                new_width = max_resolution
                new_height = int(height * (max_resolution / width))
            else:
                new_height = max_resolution
                new_width = int(width * (max_resolution / height))
        else:
            new_width = int(width * scale)
            new_height = int(height * scale)
        
        # Ensure even dimensions (required for MP4)
        new_width = new_width if new_width % 2 == 0 else new_width - 1
        new_height = new_height if new_height % 2 == 0 else new_height - 1
        
        # Calculate output FPS
        output_fps = min(target_fps, original_fps * settings["fps_reduction"])
        output_fps = max(12, output_fps)  # Minimum 12 FPS
        
        print(f"Output: {new_width}x{new_height}, {output_fps:.1f} FPS")
        
        # Use FFmpeg-style compression with OpenCV
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(
            str(output_path), 
            fourcc, 
            output_fps, 
            (new_width, new_height)
        )
        
        if not writer.isOpened():
            raise RuntimeError("Could not create output video")
        
        # Frame processing
        frame_skip = max(1, int(original_fps / output_fps))
        frame_count = 0
        written_frames = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Skip frames to achieve target FPS
            if frame_count % frame_skip == 0:
                # Resize frame
                resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                
                # Apply compression-friendly processing
                # Slight blur to reduce high-frequency noise
                resized = cv2.GaussianBlur(resized, (3, 3), 0.5)
                
                # Reduce color depth slightly for better compression
                resized = (resized / 4).astype(np.uint8) * 4
                
                writer.write(resized)
                written_frames += 1
                
                # Memory cleanup
                del resized
                
            del frame
            frame_count += 1
            
            # Periodic garbage collection
            if frame_count % 100 == 0:
                gc.collect()
        
        print(f"Processed {frame_count} frames, wrote {written_frames} frames")
        
    finally:
        cap.release()
        writer.release()
        gc.collect()
    
    return str(output_path)

def get_video_info(file_path):
    """Get video file information"""
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        return None
    
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps
        
        return {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration": duration
        }
    finally:
        cap.release()

# Legacy function for backwards compatibility
def compress_video(in_path, out_path, palette_sample_rate=5, frame_limit=0, max_colors=64, quality_params=None):
    """
    Legacy function - redirects to direct compression
    """
    quality_map = {
        1: "ultra",
        2: "high", 
        3: "medium",
        4: "low"
    }
    
    skip_frames = quality_params.get("skip_frames", 2) if quality_params else 2
    quality = quality_map.get(skip_frames, "medium")
    
    return compress_video_direct(in_path, out_path, quality)