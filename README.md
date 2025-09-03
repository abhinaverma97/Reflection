# LifeCoach AI - Your Personal AI Life Coach

A modern glassmorphism-styled website with an integrated Google Gemini AI-powered life coach chatbot.

![LifeCoach AI Website](screenshots/website.png)

## Features

- **Modern Glassmorphism Design** - Beautiful, modern UI with glassmorphism effects
- **Responsive Layout** - Works on all devices from mobile to desktop
- **AI-Powered Life Coach** - Real-time communication with the Gemini AI model
- **Complete Website** - Includes header, hero section, about section, testimonials, and footer
- **Smooth Transitions** - Scroll animations and smooth navigation
- **Interactive Chat Interface** - Timestamp for each message and loading indicators

## Technology Stack

- **Backend**: Flask (Python)
- **AI Model**: Google Gemini AI
- **Frontend**: HTML, CSS, JavaScript
- **Design**: Glassmorphism with responsive layout

## Prerequisites

- Python 3.7 or higher
- Flask
- Google Generative AI Python SDK

## Setup

1. Clone or download this repository.

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your Google AI API key:
   - The API key is already included in the code, but for security in a production environment, you should replace it with an environment variable

4. Add avatar images:
   - Place your desired avatar images in the `static` folder:
     - `ai-avatar.png` - Image for the AI avatar
     - `user-avatar.png` - Image for the user avatar
   - You can use any PNG images with a 1:1 aspect ratio (square images work best)

## Running the Application

1. Run the Flask application:
   ```
   python lifeCoach.py
   ```

2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

3. You should see the complete website with the chat interface where you can interact with the AI life coach.

## Website Structure

- **Header** - Navigation menu with links to different sections
- **Hero Section** - Introduction and call-to-action button
- **About Section** - Features and benefits of using LifeCoach AI
- **Chat Section** - Interactive chat interface to communicate with the AI
- **Testimonials** - User reviews and success stories
- **Footer** - Additional links and information

## Customization

- **Styling**: Modify the CSS in `static/style.css`
- **Content**: Update text and sections in `templates/index.html`
- **AI Behavior**: Adjust the Gemini model parameters in `lifeCoach.py`
- **Colors**: Change the gradient and color scheme in the CSS variables
- **Animation**: Add or modify animations and transitions

## Design Inspiration

The glassmorphism design was inspired by modern web applications like [Reflect](https://reflect.app/) and follows the trend of glass-like UI elements with blur effects.

## License

This project is open-source and available for personal and commercial use.

## Acknowledgements

- Google Gemini AI for powering the chatbot
- Flask for the lightweight web framework
- Glassmorphism UI trend for design inspiration 