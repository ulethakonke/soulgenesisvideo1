import streamlit as st
import tempfile
import os
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

col1, col2 = st.columns(2)
with col1:
    palette_sample_rate = st.number_input(
        "Frame sampling rate", 
        min_value=2, 
        value=5, 
        max_value=10,
        help="Take every Nth frame (5 = good balance)"
    )
    
with col2:
    max_colors = st.number_input(
        "Palette colors", 
        min_value=16, 
        max_value=128, 
        value=64, 
        help="Colors in palette (64 = good balance)"
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

if uploaded_file is not None and not st.session_state.compress_complete:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_input:
            tmp_input.write(uploaded_file.read())
            in_path = tmp_input.name
        
        out_path = str(Path(in_path).with_suffix(".genesisvid"))
        
        quality_settings = {
            "High": {"skip_frames": 1, "resize_factor": 0.7},
            "Medium": {"skip_frames": 1, "resize_factor": 0.6}, 
            "Low": {"skip_frames": 1, "resize_factor": 0.5}
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
            
        st.download_button(
            label="⬇ Download Compressed File (.genesisvid)",
            data=compressed_data,
            file_name="compressed.genesisvid",
            mime="application/octet-stream"
        )
        
        st.session_state.compress_complete = True
        
        try:
            os.unlink(in_path)
            os.unlink(out_path)
        except:
            pass
            
    except Exception as e:
        st.error(f"Error during compression: {str(e)}")

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
        
        with st.spinner("Decompressing video..."):
            decompress_video(in_path, out_path)
        
        st.success("✅ Decompression complete!")
        
        with open(out_path, "rb") as f:
            video_data = f.read()
            
        st.download_button(
            label="⬇ Download Reconstructed Video (.mp4)",
            data=video_data,
            file_name="reconstructed.mp4",
            mime="video/mp4"
        )
        
        try:
            os.unlink(in_path)
            os.unlink(out_path)
        except:
            pass
            
    except Exception as e:
        st.error(f"Error during decompression: {str(e)}")

st.markdown("---")
st.markdown("**SoulGenesis Video Compressor** - Custom video compression with palette-based encoding")