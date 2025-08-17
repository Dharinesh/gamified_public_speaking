from flask import render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
import logging

from managers.transcription_manager import TranscriptionManager
from managers.ai_manager import AIManager
from managers.game_manager import GameManager
from services.auth_routes import create_auth_routes

logger = logging.getLogger(__name__)

def create_routes(app, db_manager, auth_manager):
    # Initialize managers
    transcription_manager = TranscriptionManager()
    ai_manager = AIManager()
    game_manager = GameManager(db_manager)
    
    # Register auth routes
    create_auth_routes(app, auth_manager)
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('login.html')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        try:
            levels = game_manager.get_all_levels(current_user.id)
            user_stats = auth_manager.get_user_statistics(current_user.id)
            recent_speeches = game_manager.get_user_speech_history(current_user.id, 5)
            
            return render_template('dashboard.html', 
                                 levels=levels, 
                                 user_stats=user_stats,
                                 recent_speeches=recent_speeches)
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            flash('Error loading dashboard', 'error')
            return render_template('dashboard.html', levels=[], user_stats={}, recent_speeches=[])
    
    @app.route('/level/<int:level_number>')
    @login_required
    def level_page(level_number):
        try:
            if not game_manager.is_level_unlocked(current_user.id, level_number):
                flash('Complete previous levels to unlock this one', 'warning')
                return redirect(url_for('dashboard'))
            
            level = game_manager.get_level_details(level_number, current_user.id)
            if not level:
                flash('Level not found', 'error')
                return redirect(url_for('dashboard'))
            
            return render_template('level.html', level=level)
        except Exception as e:
            logger.error(f"Level page error: {e}")
            flash('Error loading level', 'error')
            return redirect(url_for('dashboard'))
    
    @app.route('/quick-task')
    @login_required
    def quick_task():
        try:
            task = ai_manager.generate_quick_task()
            return render_template('quick_task.html', task=task)
        except Exception as e:
            logger.error(f"Quick task error: {e}")
            flash('Error generating quick task', 'error')
            return redirect(url_for('dashboard'))
    
    @app.route('/profile')
    @login_required
    def profile():
        try:
            user_stats = auth_manager.get_user_statistics(current_user.id)
            speech_history = game_manager.get_user_speech_history(current_user.id, 20)
            levels_progress = game_manager.get_all_levels(current_user.id)
            
            return render_template('profile.html', 
                                 user_stats=user_stats,
                                 speech_history=speech_history,
                                 levels_progress=levels_progress)
        except Exception as e:
            logger.error(f"Profile error: {e}")
            flash('Error loading profile', 'error')
            return redirect(url_for('dashboard'))
    
    @app.route('/api/upload-audio', methods=['POST'])
    @login_required
    def upload_audio():
        try:
            if 'audio' not in request.files:
                return jsonify({'error': 'No audio file provided'}), 400
            
            audio_file = request.files['audio']
            level_number = request.form.get('level_number', type=int)
            task_id = request.form.get('task_id', type=int)
            is_quick_task = request.form.get('is_quick_task', 'false').lower() == 'true'
            task_prompt = request.form.get('task_prompt', '')
            
            if audio_file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Determine file extension and MIME type
            import time
            timestamp = int(time.time())
            
            # Check the actual file content to determine format
            filename = audio_file.filename.lower()
            if filename.endswith('.wav') or 'wav' in str(audio_file.content_type):
                file_extension = '.wav'
                content_type = 'audio/wav'
            elif filename.endswith('.mp3') or 'mp3' in str(audio_file.content_type):
                file_extension = '.mp3'
                content_type = 'audio/mpeg'
            else:
                # Default to WebM but we'll handle it specially
                file_extension = '.webm'
                content_type = 'audio/webm'
            
            filename = f"user_{current_user.id}_{timestamp}{file_extension}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            
            # Save the audio file
            audio_file.save(filepath)
            
            # Verify file was saved and has content
            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                return jsonify({'error': 'Failed to save audio file'}), 500
            
            logger.info(f"Audio file saved: {filepath}, size: {os.path.getsize(filepath)} bytes, type: {content_type}")
            
            # Get audio duration
            audio_duration = transcription_manager.get_audio_duration(filepath)
            
            # Transcribe audio with format information
            transcription, error = transcription_manager.transcribe_audio(filepath, content_type)
            if error:
                logger.error(f"Transcription failed: {error}")
                return jsonify({'error': f'Transcription failed: {error}'}), 500
            
            if not transcription or len(transcription.strip()) < 5:
                return jsonify({'error': 'Could not transcribe audio or speech too short'}), 400
            
            logger.info(f"Transcription successful: {transcription[:100]}...")
            
            # Analyze speech with AI
            ai_feedback = ai_manager.analyze_speech(transcription, task_prompt)
            
            # Save response to database
            response_id = game_manager.save_speech_response(
                current_user.id, level_number, task_id, 
                transcription, ai_feedback, audio_duration, is_quick_task
            )
            
            # Update user statistics
            auth_manager.update_user_statistics(current_user.id, ai_feedback)
            
            # Calculate and save level completion if not quick task
            if not is_quick_task and level_number:
                score = game_manager.calculate_level_score(ai_feedback)
                if score >= 60:  # Passing score
                    game_manager.complete_level(current_user.id, level_number, score)
            
            # Clean up audio file
            try:
                os.remove(filepath)
            except:
                pass
            
            return jsonify({
                'success': True,
                'transcription': transcription,
                'analysis': ai_feedback,
                'response_id': response_id
            })
            
        except Exception as e:
            logger.error(f"Upload audio error: {e}")
            return jsonify({'error': 'Processing failed'}), 500
    
    @app.route('/api/generate-quick-task')
    @login_required
    def generate_quick_task_api():
        try:
            task = ai_manager.generate_quick_task()
            return jsonify(task)
        except Exception as e:
            logger.error(f"Generate quick task API error: {e}")
            return jsonify({'error': 'Failed to generate task'}), 500
    
    @app.route('/api/leaderboard')
    @login_required
    def leaderboard_api():
        try:
            leaderboard = game_manager.get_leaderboard(20)
            return jsonify(leaderboard)
        except Exception as e:
            logger.error(f"Leaderboard API error: {e}")
            return jsonify({'error': 'Failed to load leaderboard'}), 500
    
    @app.route('/favicon.ico')
    def favicon():
        return '', 204  # No content response for favicon
    
    @app.errorhandler(404)
    def not_found(error):
        try:
            return render_template('404.html'), 404
        except:
            # Fallback if template is missing
            return '''
            <h1>404 - Page Not Found</h1>
            <p>The page you're looking for doesn't exist.</p>
            <a href="/">Go Home</a>
            ''', 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        try:
            return render_template('500.html'), 500
        except:
            # Fallback if template is missing
            return '''
            <h1>500 - Internal Server Error</h1>
            <p>Something went wrong. Please try again later.</p>
            <a href="/">Go Home</a>
            ''', 500