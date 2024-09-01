import streamlit as st
import boto3
import os
import time
import requests  # to fetch the transcript from S3 URL
from pydub import AudioSegment
from pydub.utils import which
from datetime import datetime  # for generating unique job names

# Configure FFmpeg path manually if not detected
ffmpeg_path = which("ffmpeg")
if ffmpeg_path is None:
    ffmpeg_path = "C:\\ffmpeg\\bin\\ffmpeg.exe"  # Replace with the actual path to ffmpeg.exe on your machine
AudioSegment.converter = ffmpeg_path

# Function to save the uploaded audio file
def save_audio_file(audio_bytes, file_name):
    with open(file_name, "wb") as f:
        f.write(audio_bytes)
    return file_name

# Function to upload the audio file to S3
def upload_to_s3(file_name, bucket_name, s3_key):
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(file_name, bucket_name, s3_key)
        st.success(f"Uploaded {file_name} to S3 bucket {bucket_name} with key {s3_key}.")
    except Exception as e:
        st.error(f"Failed to upload to S3: {e}")

# Function to start transcription job using AWS Transcribe
def start_transcription_job(job_name, file_uri):
    transcribe_client = boto3.client('transcribe')
    try:
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': file_uri},
            MediaFormat='wav',
            LanguageCode='en-US'
        )
        st.info(f"Transcription job '{job_name}' started.")
    except Exception as e:
        st.error(f"Failed to start transcription job: {e}")

# Function to check and get the transcription result
def get_transcription_result(job_name):
    transcribe_client = boto3.client('transcribe')
    while True:
        result = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        status = result['TranscriptionJob']['TranscriptionJobStatus']
        if status == 'COMPLETED':
            transcript_uri = result['TranscriptionJob']['Transcript']['TranscriptFileUri']
            st.success(f"Transcription completed!")
            return transcript_uri  # Return the URL of the transcription JSON
        elif status == 'FAILED':
            st.error("Transcription failed.")
            return None
        else:
            st.info("Transcription in progress...")
            time.sleep(5)

# Function to download and extract the transcript text from JSON
def download_and_extract_transcript(transcript_uri):
    response = requests.get(transcript_uri)
    transcript_json = response.json()
    transcript_text = transcript_json['results']['transcripts'][0]['transcript']
    return transcript_text

# Function to generate a unique transcription job name
def generate_transcribe_job_name(base_name="TranscriptionJob"):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{base_name}_{timestamp}"

# Streamlit UI setup
st.title("Voice to Text Transcription System")

# Record or upload an audio file
audio_file = st.file_uploader("Upload an audio file", type=["wav"])

if audio_file is not None:
    # Read the file as bytes
    audio_bytes = audio_file.read()
    audio_file_path = save_audio_file(audio_bytes, "recording.wav")
    st.write(f"Audio file saved at {audio_file_path}")

    # AWS S3 bucket information (Replace with your actual S3 bucket details)
    bucket_name = 'audiobucketdemo'  # Replace with your actual S3 bucket name
    s3_key = 'recordings/recording.wav'  # S3 key for the uploaded file
    upload_to_s3(audio_file_path, bucket_name, s3_key)

    # Start transcription job
    s3_audio_uri = f's3://{bucket_name}/{s3_key}'
    transcribe_job_name = generate_transcribe_job_name()  # Automatically generate a unique job name
    start_transcription_job(transcribe_job_name, s3_audio_uri)

    # Fetch transcription result
    transcript_uri = get_transcription_result(transcribe_job_name)
    
    # If transcription completed successfully, download and display the transcript
    if transcript_uri:
        transcript_text = download_and_extract_transcript(transcript_uri)
        st.write("Transcription Result:")
        st.text_area("Transcript", value=transcript_text, height=200)
        
        # Provide a download button for the transcript
        st.download_button(
            label="Download Transcript",
            data=transcript_text,
            file_name="transcript.txt",
            mime="text/plain"
        )
