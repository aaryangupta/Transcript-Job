import streamlit as st
import boto3
import requests
from pydub import AudioSegment
import os

# Initialize AWS credentials using Streamlit secrets
aws_access_key_id = st.secrets["aws_access_key_id"]
aws_secret_access_key = st.secrets["aws_secret_access_key"]
region_name = st.secrets["aws_region"]

# Initialize S3 and Transcribe clients
s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region_name
)

transcribe_client = boto3.client(
    'transcribe',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region_name
)

# Function to save audio file locally
def save_audio_file(audio_bytes, filename):
    with open(filename, "wb") as f:
        f.write(audio_bytes)
    return filename

# Function to upload file to S3
def upload_to_s3(filename, bucket_name, object_name):
    s3_client.upload_file(filename, bucket_name, object_name)

# Function to create a transcription job
def create_transcription_job(job_name, s3_uri, bucket_name, output_key):
    response = transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': s3_uri},
        MediaFormat='wav',
        LanguageCode='en-US',
        OutputBucketName=bucket_name,
        OutputKey=output_key
    )
    return response

# Function to check the status of the transcription job
def check_transcription_job_status(job_name):
    response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
    return response['TranscriptionJob']['TranscriptionJobStatus']

# Streamlit UI components
st.title("Voice to Text Transcription App")

st.write("Record your voice, and we will transcribe it for you!")

# Audio recorder in Streamlit
audio_bytes = st.audio_recorder()

if audio_bytes:
    st.success("Audio recorded successfully!")
    audio_file_path = save_audio_file(audio_bytes, "recording.wav")

    # Upload to S3
    bucket_name = "your-s3-bucket-name"  # replace with your S3 bucket name
    object_name = "recordings/recording.wav"
    upload_to_s3(audio_file_path, bucket_name, object_name)
    st.success(f"File uploaded to S3 bucket '{bucket_name}' successfully!")

    # Create a transcription job
    s3_uri = f"s3://{bucket_name}/{object_name}"
    job_name = "auto-transcribe-job"  # fixed job name
    output_key = "transcriptions/transcription.json"
    create_transcription_job(job_name, s3_uri, bucket_name, output_key)
    st.info("Transcription job created successfully! Please wait...")

    # Check transcription status
    status = check_transcription_job_status(job_name)
    if status == 'COMPLETED':
        st.success("Transcription completed successfully!")
        
        # Construct the URL for the output file in S3
        output_url = f"https://{bucket_name}.s3.amazonaws.com/{output_key}"
        st.write("Download your transcription:")
        st.markdown(f"[Download transcription](output_url)", unsafe_allow_html=True)

    elif status == 'FAILED':
        st.error("Transcription job failed. Please try again.")
    else:
        st.info("Transcription job is in progress. Please wait...")

    # Cleanup local file after processing
    os.remove(audio_file_path)
