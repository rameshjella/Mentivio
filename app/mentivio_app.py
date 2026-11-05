import streamlit as st
from app.lesson_engine import render_lesson

st.set_page_config(page_title="Mentivio", page_icon="📚", layout="wide")


st.title("Mentivio")
st.subheader("Understand visually. Learn in any language.")

with st.sidebar:
    st.header("Create Lesson")
    country = st.selectbox("Country", ["India"])
    board = st.selectbox("Education Board", ["CBSE"])
    class_name = st.selectbox("Class / Grade", ["10"])
    subject = st.selectbox("Subject", ["Mathematics"])
    chapter = st.selectbox("Chapter", ["Triangles"])
    topic = st.selectbox("Topic", ["Similar Triangles and Basic Proportionality Theorem (BPT)"])
    language = st.selectbox("Teaching language", ["English", "Telugu"])
    subtitle_language = st.selectbox("Secondary subtitle language", ["English", "Telugu"])
    duration = st.slider("Video duration (minutes)", 3, 5, 4)
    fps = st.selectbox("Frame rate", [24, 25, 30], index=0)
    difficulty = st.selectbox("Learning difficulty", ["Standard"])
    style = st.selectbox("Explanation style", ["Visual + Concept-focused"])
    if st.button("Create an Animated Lesson", type="primary"):
        with st.spinner("Generating lesson scenes, narration, and MP4 locally..."):
            result = render_lesson(language=language, subtitle_language=subtitle_language, fps=fps)
            st.session_state["video_path"] = result["video_path"]
            st.session_state["srt_path"] = result["subtitle_path"]
            st.session_state["script_path"] = result["script_path"]
            st.session_state["scene_breakdown_path"] = result["scene_breakdown_path"]
            st.session_state["validation_report_path"] = result["validation_report_path"]
            st.session_state["narration_status"] = result["narration_status"]
            st.session_state["render_metrics"] = {
                "duration_seconds": round(result["duration_seconds"], 3),
                "fps": round(result["fps"], 3),
            }
            st.success("Lesson rendered successfully.")

if "video_path" in st.session_state:
    st.video(st.session_state["video_path"])
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        with open(st.session_state["video_path"], "rb") as video_file:
            st.download_button("Download MP4", data=video_file.read(), file_name="mentivio_bpt_lesson_with_audio.mp4", mime="video/mp4")
    with col2:
        with open(st.session_state["srt_path"], "rb") as srt_file:
            st.download_button("Download Subtitles", data=srt_file.read(), file_name=st.session_state["srt_path"].split("/")[-1], mime="text/plain")
    with col3:
        with open(st.session_state["script_path"], "rb") as script_file:
            st.download_button("Download Script", data=script_file.read(), file_name="lesson_script.json", mime="application/json")
    with col4:
        with open(st.session_state["scene_breakdown_path"], "rb") as scene_file:
            st.download_button("Download Scene Breakdown", data=scene_file.read(), file_name="scene_breakdown.json", mime="application/json")
    with col5:
        with open(st.session_state["validation_report_path"], "rb") as report_file:
            st.download_button("Download Validation Report", data=report_file.read(), file_name="validation_report.json", mime="application/json")
    st.info(st.session_state["narration_status"])
    st.json(st.session_state["render_metrics"])

st.markdown(
    """
    ### Feature focus
    - CBSE Class 10 Mathematics: Triangles and BPT
    - 24-30 FPS local rendering with timed scene animation
    - Output: MP4, subtitle file, script, scene breakdown, validation report
    - Honest local fallback when Telugu TTS voice is unavailable
    """
)
