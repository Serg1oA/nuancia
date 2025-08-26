# Nuancia

A smart translation tool that analyzes and preserves the emotional tone of text across different languages.

## 🌟 Features

- **Emotion Analysis**: Detects 7 different emotions (joy, sadness, anger, fear, surprise, disgust, neutral)
- **Smart Translation**: Generates 3 different translation approaches
- **Visual Analytics**: Interactive charts showing emotional fingerprint comparison
- **Tone Preservation**: Maintains emotional context across languages

## 🚀 Live Demo

[View Live Application](your-render-url-here)

## 🛠️ Technologies Used

**Frontend:**
- Vanilla HTML/CSS/JavaScript
- Chart.js for data visualization

**Backend:**
- Python Flask
- Hugging Face Transformers API for ML models
- RESTful API design

**Deployment:**
- Render (free tier)
- Environment variable management

## 📊 How It Works

1. **Input Analysis**: Analyzes emotional content of source text
2. **Multi-Modal Translation**: Generates translations using different approaches:
   - Basic translation
   - Emotion-aware translation  
   - Style-aware translation
3. **Comparison Visualization**: Shows before/after emotional fingerprints

## 🔧 Local Development

1. Clone the repository
```bash
git clone https://github.com/yourusername/emotion-translator
cd emotion-translator
```

2. Set up backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create `.env` file in backend folder
```
HF_TOKEN=your_huggingface_token_here
```

4. Run the application
```bash
python app.py
```

5. Open http://localhost:5000

## 🔑 API Endpoints

- `GET /` - Serve frontend application
- `POST /api/translate` - Analyze and translate text with emotion preservation

## 📈 Project Goals

This project demonstrates:
- **Full-stack development** skills
- **API integration** with external ML services
- **Data visualization** capabilities
- **Clean code** organization and documentation
- **Production deployment** experience

## 🤝 Contributing

This is a portfolio project, but suggestions and feedback are welcome!

## 📄 License

MIT License - feel free to use this code for learning purposes.