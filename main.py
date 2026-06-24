"""MovieMatch entry point.

Run with:  python main.py   
(Make sure your TMDB API key is set in a .env file — see .env.example.)
"""

from moviematch.gui.app import launch

if __name__ == "__main__":
    launch()
