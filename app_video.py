import streamlit as st
import tempfile
import os
import cv2
import gc
from pathlib import Path
from compress_video import compress_video_direct, get_video_info

st.set_page_config(page_title="SoulGenesis Video Compressor", page_icon="🎥")

# Auto-clear cache function
def auto_clear_cache():
    st.cache_data.clear()
    gc.collect()

st.title("🎥 SoulGenesis Video Compressor")
st.markdown("**Direct MP4 Compression** - Compress videos directly without intermediate files")

# Auto memory management
if "compression_count" not in st.session_state:
    st.session_state.compression_count = 0

# Auto-clear cache every 2 operations
if st.session_state.compression_count > 0 and st.session_state.compression_count % 2 == 0:
    auto_clear_cache()
    st.session_state.compression_count = 0

uploaded_file = st.file_uploader(
    "Upload MP4/MOV", 
    type=["mp4", "mov", "avi", "mkv"], 
    key="video_uploader"
)

if uploaded_file is not None:
    file_size_mb = len(uploaded_file.getvalue()) / 1024 / 1024
    
    # File size warnings
    if file_size_mb > 200:
        st.error(f"⚠️ File too large ({file_size_mb:.1f} MB). Please use files under 200MB for best performance.")
        st.stop()
    elif file_size_mb > 100:
        st.warning(f"⚠️ Large file ({file_size_mb:.1f} MB). Processing may take several minutes.")
    else:
        st.info(f"📁 File size: {file_size_mb:.1f} MB")

# Simplified settings
col1, col2 = st.columns(2)
with col1:
    quality = st.selectbox(
        "Compression Level", 
        ["Ultra (Smallest)", "High", "Medium", "Low (Best Quality)"], 
        index=1,
        help="Ultra gives smallest files, Low preserves most quality"
    )
    
with col2:
    max_resolution = st.selectbox(
        "Max Resolution",
        [360, 480, 720, 1080],
        index=1,
        help="Videos larger than this will be scaled down"
    )

col3, col4 = st.columns(2)
with col3:
    target_fps = st.selectbox(
        "Target FPS",
        [15, 20, 24, 30],
        index=1,
        help="Lower FPS = smaller file size"
    )

with col4:
    preserve_duration = st.checkbox(
        "Preserve full duration", 
        value=True,
        help="Maintain original video length"
    )

if uploaded_file is not None:
    # Process video
    if st.button("🚀 Compress Video", type="primary"):
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_input:
                tmp_input.write(uploaded_file.read())
                input_path = tmp_input.name
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_output:
                output_path = tmp_output.name
            
            # Get original video info
            original_info = get_video_info(input_path)
            if original_info:
                st.info(f"📹 Original: {original_info['width']}x{original_info['height']}, "
                       f"{original_info['fps']:.1f} FPS, {original_info['duration']:.1f}s")
            
            # Map quality settings
            quality_map = {
                "Ultra (Smallest)": "ultra",
                "High": "high",
                "Medium": "medium", 
                "Low (Best Quality)": "low"
            }
            quality_preset = quality_map[quality]
            
            # Adjust FPS for duration preservation
            if preserve_duration and original_info:
                # Ensure we don't reduce FPS too much
                min_fps = max(12, original_info['fps'] * 0.6)
                target_fps = max(target_fps, min_fps)
            
            # Compression with progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("Compressing video..."):
                status_text.text("Processing frames...")
                progress_bar.progress(30)
                
                compress_video_direct(
                    input_path, 
                    output_path, 
                    quality_preset=quality_preset,
                    target_fps=target_fps,
                    max_resolution=max_resolution
                )
                
                progress_bar.progress(90)
                status_text.text("Finalizing...")
                
                # Get compressed video info
                compressed_info = get_video_info(output_path)
                
                progress_bar.progress(100)
                status_text.text("Complete!")
            
            st.success("✅ Compression complete!")
            
            # Read compressed file
            with open(output_path, "rb") as f:
                compressed_data = f.read()
            
            # Show results
            original_size = len(uploaded_file.getvalue())
            compressed_size = len(compressed_data)
            compression_ratio = (1 - compressed_size/original_size) * 100
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Original Size", f"{original_size/1024/1024:.1f} MB")
            with col2:
                st.metric("Compressed Size", f"{compressed_size/1024/1024:.1f} MB")
            with col3:
                st.metric("Size Reduction", f"{compression_ratio:.1f}%")
            
            # Duration comparison
            if original_info and compressed_info:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Original Duration", f"{original_info['duration']:.1f}s")
                with col2:
                    st.metric("Compressed Duration", f"{compressed_info['duration']:.1f}s")
                
                duration_ratio = (compressed_info['duration'] / original_info['duration']) * 100
                if duration_ratio < 80:
                    st.warning(f"⚠️ Duration reduced to {duration_ratio:.1f}% of original")
                else:
                    st.success(f"✅ Duration preserved: {duration_ratio:.1f}% of original")
            
            # Download button
            output_filename = f"compressed_{uploaded_file.name.split('.')[0]}.mp4"
            st.download_button(
                label="⬇️ Download Compressed Video",
                data=compressed_data,
                file_name=output_filename,
                mime="video/mp4"
            )
            
            # Update compression counter
            st.session_state.compression_count += 1
            
            # Cleanup
            try:
                os.unlink(input_path)
                os.unlink(output_path)
                del compressed_data
                auto_clear_cache()
            except:
                pass
                
        except Exception as e:
            st.error(f"❌ Compression failed: {str(e)}")
            st.info("💡 Try using a smaller file or different quality settings")

# Tips section
with st.expander("💡 Compression Tips"):
    st.markdown("""
    **For best compression:**
    - **Ultra**: 70-90% size reduction, good for sharing/previews
    - **High**: 60-80% size reduction, balanced quality/size
    - **Medium**: 40-60% size reduction, good quality retention
    - **Low**: 20-40% size reduction, minimal quality loss
    
    **Resolution guide:**
    - **360p**: Social media, very small files
    - **480p**: Good balance for most uses
    - **720p**: Good quality, moderate file size
    - **1080p**: High quality, larger files
    
    **FPS guide:**
    - **15 FPS**: Smallest files, slideshow-like
    - **20 FPS**: Good for most content
    - **24 FPS**: Standard video, smooth motion
    - **30 FPS**: Very smooth, larger files
    """)

st.markdown("---")
st.markdown("**SoulGenesis Video Compressor v3.0** - Direct MP4 compression for real file size reduction")

# Memory status (simplified)
if st.session_state.compression_count > 0:
    st.caption(f"Compressions this session: {st.session_state.compression_count} | Auto-cleanup every 2 operations")