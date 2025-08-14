import streamlit as st
import tempfile
import os
from pathlib import Path
from compress_video import compress_video, decompress_video

st.title("🎥 SoulGenesis Video Compressor")

# Initialize session state
if "compress_complete" not in st.session_state:
    st.session_state.compress_complete = False

st.header("Compress a video → .genesisvid")
uploaded_file = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov", "mpeg4"], key="compress_uploader")

palette_sample_rate = st.number_input(
    "Sample every N frames", min_value=1, value=2, help="1=Best quality, 2=Good balance, 3+=Smaller file"
)
frame_limit = st.number_input(
    "Limit frames (0 = all)", min_value=0, value=0
)

col1, col2 = st.columns([1, 1])
with col1:
    quality = st.selectbox("Compression Quality", 
                          ["High", "Medium", "Low"], 
                          index=1)
with col2:
    max_colors = st.number_input("Max palette colors", min_value=16, max_value=256, value=128, help="More colors = better quality, larger file")

if uploaded_file is not None and not st.session_state.compress_complete:
    try:
        # Create unique temp file paths
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_input:
            tmp_input.write(uploaded_file.read())
            in_path = tmp_input.name
        
        # Create output path
        out_path = str(Path(in_path).with_suffix(".genesisvid"))
        
        # Set quality parameters - focus on resolution and colors, not frame skipping
        quality_params = {
            "High": {"skip_frames": 1, "resize_factor": 0.9},
            "Medium": {"skip_frames": 1, "resize_factor": 0.7}, 
            "Low": {"skip_frames": 1, "resize_factor": 0.5}
        }
        
        with st.spinner("Compressing video..."):
            # Compress the video
            compress_video(in_path, out_path, palette_sample_rate, frame_limit, 
                         max_colors, quality_params[quality])
        
        st.success("✅ Compression complete!")
        
        # Read the compressed file and offer download
        with open(out_path, "rb") as f:
            compressed_data = f.read()
            
        # Show compression stats
        original_size = len(uploaded_file.getvalue())
        compressed_size = len(compressed_data)
        compression_ratio = original_size / compressed_size if compressed_size > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Original Size", f"{original_size/1024/1024:.1f} MB")
        with col2:
            st.metric("Compressed Size", f"{compressed_size/1024/1024:.1f} MB") 
        with col3:
            st.metric("Compression Ratio", f"{compression_ratio:.1f}x")
            
        st.download_button(
            label="⬇ Download Compressed File (.genesisvid)",
            data=compressed_data,
            file_name="compressed.genesisvid",
            mime="application/octet-stream"
        )
        
        st.session_state.compress_complete = True
        
        # Clean up temporary files
        try:
            os.unlink(in_path)
            os.unlink(out_path)
        except:
            pass  # Don't fail if cleanup fails
            
    except Exception as e:
        st.error(f"Error during compression: {str(e)}")

# Reset button
if st.session_state.compress_complete:
    if st.button("🔄 Compress Another Video"):
        st.session_state.compress_complete = False
        st.rerun()

st.header("Reconstruct video from .genesisvid")
uploaded_genesis = st.file_uploader("Upload .genesisvid", type=["genesisvid"], key="decompress_uploader")

if uploaded_genesis is not None:
    try:
        # Create unique temp file paths
        with tempfile.NamedTemporaryFile(delete=False, suffix=".genesisvid") as tmp_input:
            tmp_input.write(uploaded_genesis.read())
            in_path = tmp_input.name
        
        # Create output path
        out_path = str(Path(in_path).with_suffix(".mp4"))
        
        # Decompress the video
        decompress_video(in_path, out_path)
        
        st.success("✅ Decompression complete!")
        
        # Read the decompressed file and offer download
        with open(out_path, "rb") as f:
            video_data = f.read()
            st.download_button(
                label="⬇ Download Reconstructed Video (.mp4)",
                data=video_data,
                file_name="reconstructed.mp4",
                mime="video/mp4"
            )
        
        # Clean up temporary files
        try:
            os.unlink(in_path)
            os.unlink(out_path)
        except:
            pass  # Don't fail if cleanup fails
            
    except Exception as e:
        st.error(f"Error during decompression: {str(e)}")