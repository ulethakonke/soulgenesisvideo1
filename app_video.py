import streamlit as st
import tempfile
import os
from pathlib import Path

# Import compression functions
try:
    from compress_video import compress_video, decompress_video
except ImportError:
    st.error("compress_video.py not found. Make sure it's in the same directory.")
    st.stop()

st.set_page_config(page_title="SoulGenesis Video Compressor", page_icon="🎥")

st.title("🎥 SoulGenesis Video Compressor")

# Initialize session state
if "compress_complete" not in st.session_state:
    st.session_state.compress_complete = False

# Compression Section
st.header("Compress a video → .genesisvid")

uploaded_file = st.file_uploader(
    "Upload MP4/MOV", 
    type=["mp4", "mov", "mpeg4"], 
    key="compress_uploader"
)

# Settings
col1, col2 = st.columns(2)
with col1:
    palette_sample_rate = st.number_input(
        "Sample every N frames", 
        min_value=2, 
        value=3, 
        help="Higher = better compression, lower quality"
    )
    
with col2:
    max_colors = st.number_input(
        "Max palette colors", 
        min_value=8, 
        max_value=64, 
        value=32, 
        help="Fewer colors = better compression"
    )

col3, col4 = st.columns(2)
with col3:
    quality = st.selectbox(
        "Compression Quality", 
        ["High", "Medium", "Low"], 
        index=1
    )
    
with col4:
    frame_limit = st.number_input(
        "Limit frames (0 = all)", 
        min_value=0, 
        value=0
    )

# Process compression
if uploaded_file is not None and not st.session_state.compress_complete:
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_input:
            tmp_input.write(uploaded_file.read())
            in_path = tmp_input.name
        
        out_path = str(Path(in_path).with_suffix(".genesisvid"))
        
        # Quality settings - more aggressive for actual compression
        quality_settings = {
            "High": {"skip_frames": 2, "resize_factor": 0.8},    # Skip every 2nd frame, 80% size
            "Medium": {"skip_frames": 3, "resize_factor": 0.6},  # Skip every 3rd frame, 60% size  
            "Low": {"skip_frames": 4, "resize_factor": 0.4}      # Skip every 4th frame, 40% size
        }
        
        with st.spinner("Compressing video... This may take a few minutes."):
            compress_video(
                in_path, 
                out_path, 
                palette_sample_rate, 
                frame_limit, 
                max_colors, 
                quality_settings[quality]
            )
        
        st.success("✅ Compression complete!")
        
        # Get file sizes
        original_size = len(uploaded_file.getvalue())
        with open(out_path, "rb") as f:
            compressed_data = f.read()
        compressed_size = len(compressed_data)
        
        # Show stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Original Size", f"{original_size/1024/1024:.1f} MB")
        with col2:
            st.metric("Compressed Size", f"{compressed_size/1024/1024:.1f} MB")
        with col3:
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 0
            st.metric("Compression Ratio", f"{compression_ratio:.1f}x")
            
        # Download button
        st.download_button(
            label="⬇ Download Compressed File (.genesisvid)",
            data=compressed_data,
            file_name="compressed.genesisvid",
            mime="application/octet-stream"
        )
        
        st.session_state.compress_complete = True
        
        # Cleanup
        try:
            os.unlink(in_path)
            os.unlink(out_path)
        except:
            pass
            
    except Exception as e:
        st.error(f"Error during compression: {str(e)}")

# Reset button
if st.session_state.compress_complete:
    if st.button("🔄 Compress Another Video"):
        st.session_state.compress_complete = False
        st.rerun()

# Decompression Section
st.header("Reconstruct video from .genesisvid")

uploaded_genesis = st.file_uploader(
    "Upload .genesisvid", 
    type=["genesisvid"], 
    key="decompress_uploader"
)

if uploaded_genesis is not None:
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".genesisvid") as tmp_input:
            tmp_input.write(uploaded_genesis.read())
            in_path = tmp_input.name
        
        out_path = str(Path(in_path).with_suffix(".mp4"))
        
        with st.spinner("Decompressing video..."):
            decompress_video(in_path, out_path)
        
        st.success("✅ Decompression complete!")
        
        # Download button
        with open(out_path, "rb") as f:
            video_data = f.read()
            
        st.download_button(
            label="⬇ Download Reconstructed Video (.mp4)",
            data=video_data,
            file_name="reconstructed.mp4",
            mime="video/mp4"
        )
        
        # Cleanup
        try:
            os.unlink(in_path)
            os.unlink(out_path)
        except:
            pass
            
    except Exception as e:
        st.error(f"Error during decompression: {str(e)}")

# Footer
st.markdown("---")
st.markdown("**SoulGenesis Video Compressor** - Custom video compression with palette-based encoding")