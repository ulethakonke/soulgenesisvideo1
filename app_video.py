import streamlit as st
import tempfile
import os
import cv2
import gc  # Garbage collection
from pathlib import Path
from compress_video import compress_video
from decompress_video import decompress_video

st.set_page_config(page_title="SoulGenesis Video Compressor", page_icon="🎥")

st.title("🎥 SoulGenesis Video Compressor")

if "compress_complete" not in st.session_state:
    st.session_state.compress_complete = False

st.header("Compress a video → .genesisvid")

uploaded_file = st.file_uploader(
    "Upload MP4/MOV", 
    type=["mp4", "mov", "mpeg4"], 
    key="compress_uploader"
)

# Add file size check
if uploaded_file is not None:
    file_size_mb = len(uploaded_file.getvalue()) / 1024 / 1024
    if file_size_mb > 100:
        st.warning(f"⚠️ Large file detected ({file_size_mb:.1f} MB). Consider using Ultra quality for better memory usage.")
    elif file_size_mb > 50:
        st.info(f"📁 File size: {file_size_mb:.1f} MB - This may take a few minutes to process.")

col1, col2 = st.columns(2)
with col1:
    palette_sample_rate = st.number_input(
        "Frame sampling rate", 
        min_value=2, 
        value=3, 
        max_value=8,
        help="Take every Nth frame for palette (3 = better quality)"
    )
    
with col2:
    max_colors = st.number_input(
        "Palette colors", 
        min_value=8, 
        max_value=256, 
        value=32, 
        help="Colors in palette (32 = better compression)"
    )

col3, col4 = st.columns(2)
with col3:
    quality = st.selectbox(
        "Compression Quality", 
        ["High", "Medium", "Low", "Ultra"], 
        index=2,
        help="Lower = smaller file size"
    )
    
with col4:
    frame_limit = st.number_input(
        "Limit frames (0 = all)", 
        min_value=0, 
        value=0,
        help="Limit total frames for testing"
    )

# Advanced settings in expander
with st.expander("⚙️ Advanced Settings"):
    preserve_motion = st.checkbox(
        "Preserve motion quality", 
        value=True,
        help="Better for videos with lots of movement"
    )
    
    target_fps = st.selectbox(
        "Target playback FPS",
        [15, 20, 24, 30],
        index=1,
        help="Higher = smoother but larger file"
    )

if uploaded_file is not None and not st.session_state.compress_complete:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_input:
            tmp_input.write(uploaded_file.read())
            in_path = tmp_input.name
        
        out_path = str(Path(in_path).with_suffix(".genesisvid"))
        
        # Updated quality settings for better compression
        quality_settings = {
            "Ultra": {"skip_frames": 4, "resize_factor": 0.4},
            "High": {"skip_frames": 3, "resize_factor": 0.5},
            "Medium": {"skip_frames": 2, "resize_factor": 0.6}, 
            "Low": {"skip_frames": 1, "resize_factor": 0.7}
        }
        
        # Adjust settings based on target FPS and motion preservation
        settings = quality_settings[quality].copy()
        
        if preserve_motion and quality in ["Ultra", "High"]:
            settings["skip_frames"] = max(1, settings["skip_frames"] - 1)
        
        # Adjust frame skipping based on target FPS
        cap_temp = cv2.VideoCapture(in_path)
        original_fps = cap_temp.get(cv2.CAP_PROP_FPS) or 24
        cap_temp.release()
        
        if original_fps > target_fps:
            settings["skip_frames"] = max(settings["skip_frames"], int(original_fps / target_fps))
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("Compressing video... This may take a few minutes."):
            status_text.text("Starting compression...")
            compress_video(
                in_path, 
                out_path, 
                palette_sample_rate, 
                frame_limit, 
                max_colors, 
                settings
            )
            progress_bar.progress(100)
            
            # Force garbage collection after compression
            gc.collect()
        
        st.success("✅ Compression complete!")
        
        original_size = len(uploaded_file.getvalue())
        with open(out_path, "rb") as f:
            compressed_data = f.read()
        compressed_size = len(compressed_data)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Original Size", f"{original_size/1024/1024:.1f} MB")
        with col2:
            st.metric("Compressed Size", f"{compressed_size/1024/1024:.1f} MB")
        with col3:
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 0
            st.metric("Compression Ratio", f"{compression_ratio:.1f}x")
            
        # Show compression percentage
        compression_percent = (1 - compressed_size/original_size) * 100
        st.info(f"📊 File size reduced by {compression_percent:.1f}%")
            
        st.download_button(
            label="⬇️ Download Compressed File (.genesisvid)",
            data=compressed_data,
            file_name=f"compressed_{uploaded_file.name.split('.')[0]}.genesisvid",
            mime="application/octet-stream"
        )
        
        st.session_state.compress_complete = True
        
        try:
            os.unlink(in_path)
            os.unlink(out_path)
            # Force cleanup
            del compressed_data
            gc.collect()
        except:
            pass
            
    except Exception as e:
        st.error(f"Error during compression: {str(e)}")
        st.info("💡 Try reducing quality settings or frame limit for large videos")

if st.session_state.compress_complete:
    if st.button("🔄 Compress Another Video"):
        st.session_state.compress_complete = False
        st.rerun()

st.header("Reconstruct video from .genesisvid")

uploaded_genesis = st.file_uploader(
    "Upload .genesisvid", 
    type=["genesisvid"], 
    key="decompress_uploader"
)

if uploaded_genesis is not None:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".genesisvid") as tmp_input:
            tmp_input.write(uploaded_genesis.read())
            in_path = tmp_input.name
        
        out_path = str(Path(in_path).with_suffix(".mp4"))
        
        with st.spinner("Reconstructing video with motion smoothing..."):
            decompress_video(in_path, out_path)
        
        st.success("✅ Video reconstruction complete!")
        
        # Show file info
        genesis_size = len(uploaded_genesis.getvalue())
        with open(out_path, "rb") as f:
            video_data = f.read()
        video_size = len(video_data)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Genesis File", f"{genesis_size/1024/1024:.1f} MB")
        with col2:
            st.metric("Reconstructed Video", f"{video_size/1024/1024:.1f} MB")
            
        st.download_button(
            label="⬇️ Download Reconstructed Video (.mp4)",
            data=video_data,
            file_name=f"reconstructed_{uploaded_genesis.name.split('.')[0]}.mp4",
            mime="video/mp4"
        )
        
        st.info("🎬 The reconstructed video includes motion smoothing for better playback quality")
        
        try:
            os.unlink(in_path)
            os.unlink(out_path)
            # Force cleanup
            del video_data
            gc.collect()
        except:
            pass
            
    except Exception as e:
        st.error(f"Error during decompression: {str(e)}")
        st.info("💡 Make sure you're uploading a valid .genesisvid file")

st.markdown("---")
st.markdown("**SoulGenesis Video Compressor v2.0** - Advanced video compression with motion smoothing")
st.markdown("🔧 **New Features**: Better compression ratios, smoother playback, temporal smoothing")

# Add some tips
with st.expander("💡 Compression Tips"):
    st.markdown("""
    **For best results:**
    - Use **Ultra** quality for maximum compression (80-90% size reduction)
    - Lower palette colors (16-32) for smaller files
    - Enable motion preservation for action videos
    - Set target FPS to 20 for good balance of smoothness and size
    
    **File size expectations:**
    - Ultra: 80-90% compression
    - High: 70-80% compression  
    - Medium: 60-70% compression
    - Low: 40-60% compression
    """)