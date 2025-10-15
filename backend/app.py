"""
Healthcare Symptom Checker - Complete Backend API with FREE Google Gemini
Flask server with Google Gemini AI integration

Author: Kajal Meshram (corrected and updated with hardcoded fallback)
Date: 2025

This is the complete, ready-to-run backend server with enhanced, hardcoded safety fallbacks.
Make sure you add your GOOGLE_API_KEY in a .env file in this folder.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, List, Optional, Literal
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re
import traceback
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour", "20 per minute"],
    storage_uri="memory://"
)

# ==================== PYDANTIC SCHEMAS FOR STRUCTURED OUTPUT ====================

# 1. Define the Condition Structure
class Condition(BaseModel):
    """Schema for a single possible medical condition."""
    name: str = Field(description="Name of the possible condition, e.g., 'Common Cold'")
    probability: Literal["High", "Moderate", "Low"] = Field(description="Likelihood: High, Moderate, or Low")
    description: str = Field(description="Clear 1-2 sentence description of this condition.")
    severity: Literal["mild", "moderate", "serious"] = Field(description="Severity: mild, moderate, or serious")

# 2. Define the Final Output Structure
class SymptomAnalysisSchema(BaseModel):
    """The complete final JSON schema for the symptom analysis."""
    conditions: List[Condition] = Field(description="A list of 2 to 4 most probable medical conditions, ordered by probability.")
    urgency: Literal["urgent", "soon", "routine"] = Field(description="Classification of required follow-up time.")
    recommendations: List[str] = Field(description="5 to 7 specific, actionable recommendations for the patient.")

# ==================== DATABASE FUNCTIONS ====================

def init_db():
    """Initialize SQLite database for storing query history"""
    try:
        conn = sqlite3.connect('symptom_checker.db')
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS symptom_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                duration TEXT,
                severity TEXT,
                conditions TEXT,
                recommendations TEXT,
                urgency_level TEXT,
                session_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON symptom_queries(session_id)
        ''')
        
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON symptom_queries(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
        
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")

# Initialize database
init_db()

# ==================== SYMPTOM ANALYZER CLASS ====================

class SymptomAnalyzer:
    """LLM-based symptom analyzer using Google Gemini"""
    
    def __init__(self):
        """Initialize Google Gemini API and model"""
        api_key = os.getenv("GOOGLE_API_KEY")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found! Please add it to a .env file or environment variables."
            )
        
        # Configure the genai client
        genai.configure(api_key=api_key)

        # Initialize model and keep as instance attribute
        try:
            # Add "models/" prefix if missing, which is safer
            full_model_name = model_name if model_name.startswith("models/") else f"models/{model_name}"
            self.model = genai.GenerativeModel(full_model_name)
            print(f"✅ Google Gemini API initialized successfully with model: {full_model_name}")
        except Exception as e:
            raise RuntimeError(
                "Failed to initialize Gemini model. Check GEMINI_MODEL and that your API key has access. "
                f"Original error: {e}"
            )
            
    def analyze_symptoms(self, data: Dict) -> Dict:
        """
        Main analysis function - analyzes symptoms using Google Gemini with Structured Output
        """
        prompt = self._build_prompt(data)
        
        try:
            print("🤖 Sending request to Gemini AI with Structured Output...")

            # CRITICAL FIX: Use 'config' with response_schema for guaranteed JSON
            response = self.model.generate_content(
                prompt,
                config=genai.types.GenerateContentConfig(
                    # STRUCTURED OUTPUT SETTINGS
                    response_mime_type="application/json",
                    response_schema=SymptomAnalysisSchema, # Pydantic Model
                    
                    # Generation settings
                    temperature=0.3,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=1024,
                )
            )
            
            print("✅ Received structured response from Gemini AI")
            
            # The response.text should now be clean, valid JSON
            response_text = response.text 
            
            print(f"🧠 Gemini Response (preview): {response_text[:300]}...")
            
            return self._parse_llm_response(response_text, data)


        except Exception as e:
            print(f"❌ LLM Error: {str(e)}")
            print(f"Full traceback:\n{traceback.format_exc()}")
            return self._fallback_analysis(data)

    def _build_prompt(self, data: Dict) -> str:
        """Build comprehensive prompt for LLM"""
        prompt = f"""You are an expert medical AI assistant providing preliminary symptom assessment for EDUCATIONAL PURPOSES ONLY.

=== PATIENT INFORMATION ===
Symptoms: {data.get('symptoms', 'Not provided')}
Age: {data.get('age', 'Not provided')}
Gender: {data.get('gender', 'Not provided')}
Duration: {data.get('duration', 'Not provided')}
Severity Level: {data.get('severity', 'Not provided')}

=== YOUR TASK ===
Analyze the symptoms and provide a preliminary assessment. The output MUST strictly adhere to the provided JSON Schema (SymptomAnalysisSchema).

=== ANALYSIS GUIDELINES ===

1. POSSIBLE CONDITIONS:
    - List 2-4 most probable conditions based on symptoms
    - Order by probability (most likely first)
    - Use the defined probability and severity levels only.

2. URGENCY CLASSIFICATION:
    - Use "urgent", "soon", or "routine". Classify based on the severity of the most probable condition and the presence of emergency symptoms.
    
3. RECOMMENDATIONS:
    - Provide 5-7 specific, actionable steps.
    - Always emphasize consulting a qualified healthcare provider.

=== CRITICAL SAFETY RULES ===
1. BE CONSERVATIVE: When in doubt, recommend medical consultation
2. FLAG EMERGENCIES: Always mark serious symptoms as "urgent"
3. NO DIAGNOSIS: This is preliminary assessment only, not a diagnosis
4. EVIDENCE-BASED: Only suggest well-established possibilities

=== EMERGENCY SYMPTOMS (If any of these apply, Urgency MUST be URGENT) ===
- Chest pain or pressure
- Difficulty breathing or shortness of breath
- Severe bleeding that won't stop
- Sudden severe headache
- Sudden confusion or trouble speaking
- Sudden weakness or numbness (especially one side)
- Loss of consciousness or fainting
- Severe abdominal pain

Now analyze the symptoms and respond ONLY with the requested JSON structure."""
        return prompt
    
    def _parse_llm_response(self, response: str, original_data: Dict) -> Dict:
        """
        Parse and structure LLM response. 
        Expects clean JSON due to Structured Output feature.
        """
        try:
            response = response.strip()
            
            # CRITICAL FIX: Direct JSON loading. Regex is no longer needed!
            parsed = json.loads(response)
            
            # Validate required top-level fields
            if not all(key in parsed for key in ['conditions', 'urgency', 'recommendations']):
                raise ValueError("Missing required top-level fields in AI response structure")

            # Validate conditions format and correct urgency if needed (though Pydantic does this)
            if isinstance(parsed.get('conditions'), list) and len(parsed['conditions']) > 0:
                for condition in parsed['conditions']:
                    if not all(k in condition for k in ['name', 'probability', 'description', 'severity']):
                        raise ValueError("Invalid condition format (Missing sub-keys)")
            
            # Final safety check for urgency
            if parsed.get('urgency') not in ['urgent', 'soon', 'routine']:
                parsed['urgency'] = 'routine'
            
            # Return properly formatted analysis
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'input': original_data,
                'conditions': parsed.get('conditions', []),
                'urgency': parsed.get('urgency', 'routine'),
                'recommendations': parsed.get('recommendations', []),
                'disclaimer': True,
                'ai_model': os.getenv('GEMINI_MODEL', 'Google Gemini')
            }
                
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"⚠️ JSON Parse Error: {str(e)}")
            print(f"Raw response: {response[:200]}...")
            
            # If parsing fails, use fallback
            print("⚠️ Using fallback analysis due to parsing error")
            return self._fallback_analysis(original_data)

    
    # ==================== FALLBACK HELPER FUNCTIONS (HARDCODED) ====================
    
    def _extreme_emergency_fallback(self, data: Dict) -> Dict:
        """Fallback for immediate life-threatening symptoms (e.g., chest pain, stroke signs)."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'input': data,
            'conditions': [{
                'name': '⚠️ IMMEDIATE MEDICAL ATTENTION REQUIRED',
                'probability': 'N/A',
                'description': 'Your symptoms indicate a potentially serious, life-threatening condition that requires immediate professional evaluation.',
                'severity': 'serious'
            }],
            'urgency': 'urgent',
            'recommendations': [
                '🚨 Call emergency services (911/112) immediately',
                '🏥 Go to the nearest emergency room',
                '❌ Do NOT wait - seek help NOW',
                '📞 If alone, call someone to help you',
                '⏱️ Note when symptoms started',
                '💊 Bring list of current medications if possible'
            ],
            'disclaimer': True,
            'note': 'AI analysis unavailable - Extreme Emergency response activated',
            'ai_model': 'Fallback System (Extreme)'
        }
    
    def _gastro_safety_fallback(self, data: Dict) -> Dict:
        input_symptoms = data.get('symptoms', '').lower()
        
        # Check for key severe dehydration/emergency gastro signs to set urgency
        is_severe = any(keyword in input_symptoms for keyword in ['can\'t keep down', 'blood', 'black stools', 'fainting', 'severe weakness', 'no urine'])
        urgency_level = 'urgent' if is_severe else 'soon'

        return {
            'timestamp': datetime.utcnow().isoformat(),
            'input': data,
            'conditions': [
                {
                    "name": "Dehydration (Critical Risk)",
                    "probability": "High",
                    "description": "Significant fluid and electrolyte loss from persistent vomiting/diarrhea, leading to weakness and dizziness. Requires immediate focus on rehydration.",
                    "severity": "serious"
                },
                {
                    "name": "Viral Gastroenteritis ('Stomach Flu')",
                    "probability": "Moderate",
                    "description": "Common viral infection of the digestive tract causing vomiting and diarrhea, often resolving within a few days.",
                    "severity": "moderate"
                },
                {
                    "name": "Food Poisoning (Bacterial or Toxin-related)",
                    "probability": "Moderate",
                    "description": "Illness caused by consuming contaminated food or water. Symptoms often start quickly and can be intense.",
                    "severity": "moderate"
                },
                {
                    "name": "Traveler's Diarrhea (if recent travel)",
                    "probability": "Moderate",
                    "description": "A form of gastroenteritis usually caused by bacteria, common after traveling to areas with different sanitation practices.",
                    "severity": "mild"
                }
            ],
            'urgency': urgency_level,
            'recommendations': [
                "Sip, Don't Gulp: Drink small amounts of clear fluids (water, ORS) frequently, even if you can only keep down a few sips.",
                "Electrolytes are Key: Use Oral Rehydration Solutions (ORS) over plain water or high-sugar sports drinks.",
                "Rest: Get plenty of rest to allow your body to recover.",
                "Eat Bland Foods: When vomiting stops, start slowly with bland, easy-to-digest foods (like Bananas, Rice, Applesauce, Toast).",
                "Avoid: Fruit juice, soda, coffee, alcohol, and fatty/spicy foods.",
                "🚨 **See a Doctor Immediately if:** persistent dizziness/fainting, no urine for 8+ hours, blood in stool/vomit, or inability to keep down liquids for 24 hours.",
                "📞 Consult a healthcare provider if vomiting or diarrhea lasts more than 48 hours."
            ],
            'disclaimer': True,
            'note': f'Hardcoded Safety Response (Gastro/Dehydration) - Urgency set to: {urgency_level}',
            'ai_model': 'Fallback System (Gastro)'
        }
    
    def _safe_routine_fallback(self, data: Dict) -> Dict:
        """Fallback for general symptoms when AI fails and no specific emergency is detected."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'input': data,
            'conditions': [{
                'name': 'Professional Medical Evaluation Needed',
                'probability': 'N/A',
                'description': 'Your symptoms require in-person evaluation by a qualified healthcare provider for accurate assessment.',
                'severity': 'unknown'
            }],
            'urgency': 'soon',
            'recommendations': [
                '📅 Schedule an appointment with your primary care physician',
                '📝 Write down all your symptoms in detail before the appointment',
                '⏰ Note when symptoms started and how they have changed',
                '💊 List all medications and supplements you are currently taking',
                '📊 Monitor symptoms and record any changes',
                '🚨 Seek immediate care if symptoms suddenly worsen or become severe',
            ],
            'disclaimer': True,
            'note': 'AI analysis temporarily unavailable - General routine advice provided',
            'ai_model': 'Fallback System (General)'
        }


    def _fallback_analysis(self, data: Dict) -> Dict:
        """Master fallback function to route based on symptom severity/type."""
        symptoms_lower = data.get('symptoms', '').lower()
        
        # 1. CHECK FOR EXTREME EMERGENCIES (Triggers _extreme_emergency_fallback)
        emergency_keywords = [
            'chest pain', 'chest pressure', 'difficulty breathing', 'shortness of breath',
            'severe bleeding', 'stroke', 'can\'t move arm', 'face drooping',
            'seizure', 'convulsion', 'unconscious', 'passed out', 'fainted',
            'severe headache', 'worst headache', 'coughing blood', 'vomiting blood',
            'severe abdominal pain', 'severe stomach pain'
        ]
        if any(keyword in symptoms_lower for keyword in emergency_keywords):
            return self._extreme_emergency_fallback(data)
            
        # 2. CHECK FOR GASTRO SYMPTOMS (Triggers the detailed hardcoded response)
        gastro_keywords = ['vomiting', 'diarrhea', 'loose motion']
        dehydration_keywords = ['weakness', 'dizzy', 'faint']
        
        if (any(keyword in symptoms_lower for keyword in gastro_keywords) and 
            any(keyword in symptoms_lower for keyword in dehydration_keywords)):
            return self._gastro_safety_fallback(data)

        # 3. DEFAULT SAFE FALLBACK (for all other non-emergency failures)
        return self._safe_routine_fallback(data)

# ==================== INITIALIZE ANALYZER ====================

try:
    analyzer = SymptomAnalyzer()
except Exception as e:
    print(f"❌ CRITICAL ERROR: Could not initialize Gemini API!")
    print(f"Error: {str(e)}")
    print("\n🔑 Make sure you have:")
    print("1. Created a .env file in the backend folder")
    print("2. Added your Google API key: GOOGLE_API_KEY=your_key_here")
    print("3. Get free key from: https://aistudio.google.com/app/apikey")
    analyzer = None

# ==================== API ENDPOINTS ====================

@app.route('/', methods=['GET'])
def home():
    """Root endpoint - API information"""
    return jsonify({
        'name': 'Healthcare Symptom Checker API',
        'version': '1.0.0',
        'status': 'running',
        'ai_model': os.getenv('GEMINI_MODEL', 'Google Gemini'),
        'endpoints': {
            'health': '/health',
            'analyze': '/api/analyze (POST)',
            'history': '/api/history/<session_id> (GET)'
        },
        'documentation': 'See README.md for full documentation'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - verify API is working"""
    return jsonify({
        'status': 'healthy',
        'ai_status': 'ready' if analyzer else 'not configured',
        'ai_model': os.getenv('GEMINI_MODEL', 'Google Gemini'),
        'database': 'connected',
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'All systems operational' if analyzer else 'Configure GOOGLE_API_KEY'
    }), 200

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
@limiter.limit("10 per minute")
def api_analyze():
    """Main symptom analysis endpoint"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 204
    
    # Check if AI is available
    if not analyzer:
        return jsonify({
            'error': 'AI service not available',
            'message': 'Google Gemini API not configured. Please check GOOGLE_API_KEY in .env file.',
            'help': 'Get free API key from: https://aistudio.google.com/app/apikey'
        }), 503
    
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Validate input exists
        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Request body must contain JSON data'
            }), 400
        
        # Validate symptoms field
        if 'symptoms' not in data or not data['symptoms'].strip():
            return jsonify({
                'error': 'Symptoms field is required',
                'message': 'Please provide a "symptoms" field in your request'
            }), 400
        
        # Validate minimum length
        if len(data['symptoms'].strip()) < 10:
            return jsonify({
                'error': 'Symptoms description too short',
                'message': 'Please provide more detailed symptom description (at least 10 characters)'
            }), 400
        
        # Validate maximum length
        if len(data['symptoms']) > 2000:
            return jsonify({
                'error': 'Symptoms description too long',
                'message': 'Please limit symptom description to 2000 characters'
            }), 400
        
        # Log analysis start
        print(f"\n{'='*60}")
        print(f"🔍 NEW SYMPTOM ANALYSIS REQUEST")
        print(f"Symptoms: {data['symptoms'][:100]}...")
        print(f"Age: {data.get('age', 'N/A')}")
        print(f"Gender: {data.get('gender', 'N/A')}")
        print(f"Duration: {data.get('duration', 'N/A')}")
        print(f"Severity: {data.get('severity', 'N/A')}")
        print(f"{'='*60}\n")
        
        # Analyze symptoms using AI
        analysis = analyzer.analyze_symptoms(data)
        
        # Store in database
        store_query(data, analysis)
        
        print(f"✅ Analysis completed successfully")
        print(f"Urgency: {analysis.get('urgency', 'unknown')}")
        print(f"Conditions found: {len(analysis.get('conditions', []))}\n")
        
        return jsonify(analysis), 200
        
    except Exception as e:
        print(f"❌ Error in api_analyze: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'error': 'Internal server error',
            'message': 'Unable to process request. Please try again.',
            'details': str(e) if app.debug else 'Enable debug mode for details'
        }), 500

@app.route('/api/history/<session_id>', methods=['GET'])
@limiter.limit("30 per minute")
def get_history(session_id):
    """Get query history for a specific session"""
    try:
        conn = sqlite3.connect('symptom_checker.db')
        c = conn.cursor()
        
        # Query last 10 entries for this session
        c.execute('''
            SELECT timestamp, symptoms, conditions, urgency_level, age, gender
            FROM symptom_queries
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (session_id,))
        
        rows = c.fetchall()
        conn.close()
        
        # Format history
        history = []
        for row in rows:
            history.append({
                'timestamp': row[0],
                'symptoms': row[1][:100] + '...' if len(row[1]) > 100 else row[1],
                'conditions': json.loads(row[2]) if row[2] else [],
                'urgency': row[3],
                'age': row[4],
                'gender': row[5]
            })
        
        return jsonify({
            'session_id': session_id,
            'count': len(history),
            'history': history
        }), 200
        
    except Exception as e:
        print(f"❌ Error fetching history: {str(e)}")
        return jsonify({
            'error': 'Unable to fetch history',
            'message': str(e) if app.debug else 'Database error'
        }), 500

@app.route('/api/stats', methods=['GET'])
@limiter.limit("10 per minute")
def get_stats():
    """Get overall statistics"""
    try:
        conn = sqlite3.connect('symptom_checker.db')
        c = conn.cursor()
        
        # Get total queries
        c.execute('SELECT COUNT(*) FROM symptom_queries')
        total_queries = c.fetchone()[0]
        
        # Get queries by urgency
        c.execute('''
            SELECT urgency_level, COUNT(*) 
            FROM symptom_queries 
            GROUP BY urgency_level
        ''')
        urgency_stats = dict(c.fetchall())
        
        conn.close()
        
        return jsonify({
            'total_queries': total_queries,
            'urgency_breakdown': urgency_stats,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error fetching stats: {str(e)}")
        return jsonify({'error': 'Unable to fetch statistics'}), 500

# ==================== DATABASE HELPER ====================

def store_query(input_data: Dict, analysis: Dict):
    """Store query and analysis in database"""
    try:
        conn = sqlite3.connect('symptom_checker.db')
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO symptom_queries 
            (timestamp, symptoms, age, gender, duration, severity, 
             conditions, recommendations, urgency_level, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            input_data.get('symptoms', ''),
            input_data.get('age'),
            input_data.get('gender'),
            input_data.get('duration'),
            input_data.get('severity'),
            json.dumps(analysis.get('conditions', [])),
            json.dumps(analysis.get('recommendations', [])),
            analysis.get('urgency', 'routine'),
            input_data.get('session_id', '')
        ))
        
        conn.commit()
        conn.close()
        
        print("💾 Query stored in database successfully")
        
    except Exception as e:
        print(f"❌ Database storage error: {str(e)}")

# ==================== ERROR HANDLERS ====================

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded"""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please wait a moment and try again.',
        'retry_after': '1 minute'
    }), 429

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    print(f"❌ Internal server error: {str(e)}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on our end. Please try again.'
    }), 500

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': {
            'home': '/',
            'health': '/health',
            'analyze': '/api/analyze (POST)',
            'history': '/api/history/<session_id> (GET)',
            'stats': '/api/stats (GET)'
        }
    }), 404

# ==================== MAIN ====================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🏥 HEALTHCARE SYMPTOM CHECKER - BACKEND SERVER")
    print("="*70)
    print(f"📡 Using: {os.getenv('GEMINI_MODEL', 'Google Gemini (env GEMINI_MODEL)')}")
    print(f"🌐 Server URL: http://localhost:5000")
    print(f"🌐 Frontend URL: http://localhost:3000")
    print(f"📊 Database: SQLite (symptom_checker.db)")
    print("="*70)
    
    if not analyzer:
        print("\n⚠️ WARNING: Google Gemini API not configured!")
        print("🔑 Steps to fix:")
        print("  1. Go to: https://aistudio.google.com/app/apikey")
        print("  2. Create a free API key")
        print("  3. Create .env file in backend folder")
        print("  4. Add: GOOGLE_API_KEY=your_key_here")
        print("  6. Restart this server")
        print("\n" + "="*70 + "\n")
    else:
        print("\n✅ All systems operational!")
        print("🚀 Ready to analyze symptoms!\n")
        print("="*70 + "\n")
    
    # Run Flask development server
    app.run(
        debug=True,  # Enable debug mode for development
        host='0.0.0.0',  # Allow external connections
        port=5000,  # Port number
        threaded=True  # Handle multiple requests
    )
