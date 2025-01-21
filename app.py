from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/scrape', methods=['POST'])
def scrape():
    """
    Trigger scraping for Rightmove or OpenRent (or both).
    Expected JSON body:
      {
        "site": "rightmove" | "openrent" | "all"
      }
    """
    data = request.get_json()
    if not data or 'site' not in data:
        return jsonify({"error": "Please specify 'site' in JSON body."}), 400

    site = data['site'].lower()
    try:
        if site == 'rightmove':
            # Example command if using Scrapy (comment out if using requests+bs4)
            # subprocess.run(["scrapy", "runspider", "scrapers/rightmove_scraper.py", "-o", "rightmove_data.csv"], check=True)

            # Or call a Python function directly:
            from scrapers.rightmove_scraper import scrape_rightmove
            output_file = 'rightmove_data.csv'
            scrape_rightmove(output_csv=output_file)

            return jsonify({"message": f"Rightmove scraping complete -> {output_file}"}), 200

        elif site == 'openrent':
            # Example command if using Scrapy
            # subprocess.run(["scrapy", "runspider", "scrapers/openrent_scraper.py", "-o", "openrent_data.csv"], check=True)

            # Or call a Python function directly:
            from scrapers.openrent_scraper import scrape_openrent
            output_file = 'openrent_data.csv'
            scrape_openrent(output_csv=output_file)

            return jsonify({"message": f"OpenRent scraping complete -> {output_file}"}), 200

        elif site == 'all':
            # Scrape both
            from scrapers.rightmove_scraper import scrape_rightmove
            from scrapers.openrent_scraper import scrape_openrent

            rm_file = 'rightmove_data.csv'
            or_file = 'openrent_data.csv'
            scrape_rightmove(output_csv=rm_file)
            scrape_openrent(output_csv=or_file)

            return jsonify({
                "message": "Scraping for both sites complete",
                "files": [rm_file, or_file]
            }), 200
        else:
            return jsonify({"error": "Invalid site specified"}), 400

    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


if __name__ == '__main__':
    # Run the Flask server in debug mode (for development)
    # Access the endpoint with POST requests at http://localhost:5000/scrape
    app.run(debug=True, host='0.0.0.0', port=5000)