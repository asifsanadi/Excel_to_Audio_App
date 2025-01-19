from flask import Flask, request, render_template, send_file, jsonify, url_for
import pandas as pd
import pyttsx3
import os
import subprocess
from pydub import AudioSegment
import time

app = Flask(__name__)

# Load pause audio files into memory
pause_files = {
    'pause_1_sec': AudioSegment.from_wav('pause_1_sec.wav'),
    'pause_2_sec': AudioSegment.from_wav('pause_2_sec.wav'),
    'pause_3_sec': AudioSegment.from_wav('pause_3_sec.wav')
}

# Initialize pyttsx3 engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')
# Set male voice (this may vary depending on your system)
for voice in voices:
    if 'male' in voice.name.lower():
        engine.setProperty('voice', voice.id)
        break

# Function to generate audio segments for each part of the question
def generate_audio_segment(text, filename):
    engine.save_to_file(text, f"{filename}.mp3")
    engine.runAndWait()
    subprocess.run(["ffmpeg", "-i", f"{filename}.mp3", f"{filename}.wav"])
    os.remove(f"{filename}.mp3")
    return f"{filename}.wav"

# Function to generate audio with pauses
def generate_audio_with_pauses(audio_segments, output_path):
    combined = AudioSegment.empty()
    for segment in audio_segments:
        if segment in pause_files:
            combined += pause_files[segment]
        else:
            if os.path.exists(segment):
                combined += AudioSegment.from_wav(segment)
            else:
                print(f"File not found: {segment}")
                return
    combined.export(output_path, format="wav")
    print(f"Final audio file with pauses generated: {output_path}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/instructions')
def instructions():
    return render_template('instructions.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file:
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)
        
        try:
            data = pd.read_excel(file_path, engine='openpyxl')
            print("Excel file loaded successfully.")
        except Exception as e:
            return jsonify({"error": f"Error loading Excel file: {e}"})

        # Notify user of successful upload
        return jsonify({"message": "File uploaded successfully", "filename": file.filename})

    return jsonify({"error": "No file uploaded"})

@app.route('/process', methods=['POST'])
def process():
    filename = request.json['filename']
    file_path = os.path.join('uploads', filename)
    
    try:
        data = pd.read_excel(file_path, engine='openpyxl')
    except Exception as e:
        return jsonify({"error": f"Error loading Excel file: {e}"})

    # Create the final audio with pauses
    audio_files = []
    try:
        for i, row in data.iterrows():
            # Generate audio for each part of the question
            intro = "Let’s go through an MCQ question.\n\n" if i == 0 else "Let’s move on to the next question.\n\n"
            audio_files.append(generate_audio_segment(intro, f"intro_{i}"))
            audio_files.append(f"pause_{row['Pause After Question']}_sec")

            question_text = f"The question is: {row['Question']}\n\n"
            audio_files.append(generate_audio_segment(question_text, f"question_{i}"))
            audio_files.append(f"pause_{row['Pause After Question']}_sec")

            options_text = (
                "The options are:\n"
                f"1. {row['Option A']}.\n"
                f"2. {row['Option B']}.\n"
                f"3. {row['Option C']}.\n"
                f"4. {row['Option D']}.\n\n"
            )
            audio_files.append(generate_audio_segment(options_text, f"options_{i}"))
            audio_files.append(f"pause_{row['Pause After Options']}_sec")

            answer_text = f"The correct answer is: {row['Answer']}.\n\n"
            audio_files.append(generate_audio_segment(answer_text, f"answer_{i}"))
            audio_files.append(f"pause_{row['Pause After Answer']}_sec")

            explanation_text = f"Explanation: {row['Explanation']}\n"
            audio_files.append(generate_audio_segment(explanation_text, f"explanation_{i}"))
            audio_files.append(f"pause_{row['Pause After Explanation']}_sec")

            # Simulate processing time for progress bar
            time.sleep(1)

        print("Scripts combined successfully.")
    except Exception as e:
        return jsonify({"error": f"Error generating audio segments: {e}"})

    # Generate the final audio file with pauses
    output_file = os.path.join('outputs', f"{os.path.splitext(filename)[0]}_with_pauses.wav")
    generate_audio_with_pauses(audio_files, output_file)

    # Clean up temporary files
    for audio_file in audio_files:
        if os.path.exists(audio_file):
            os.remove(audio_file)

    # Notify user of successful processing
    return jsonify({"message": "Processing completed successfully", "output_file": os.path.basename(output_file)})

@app.route('/download/<filename>')
def download(filename):
    return send_file(os.path.join('outputs', filename), as_attachment=True)

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
    app.run(debug=True)