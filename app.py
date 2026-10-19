#################################
########### SETUP ###########
#################################

from pathlib import Path
from flask import Flask, render_template, request, redirect, jsonify
import database.db_connector as db
from flask_cors import CORS
import os
from scripts.identifier.identify_one_img import classify_image, classify_image_from_url

from PIL import Image
import subprocess

PORT = 8001

app = Flask(__name__)

# Allows requests from the React dev server (Vite defaults to port 5173).
# Without this, the browser blocks React's fetch() calls to Flask with a
# CORS error, since they're on different origins (5173 vs 8001).
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

# JSON API version of the birds data, for the React compendium page.
# Unlike avidex_birds() above, this returns raw data instead of rendering
# a template -- React (BirdCard components) does the rendering itself.
@app.route("/api/birds", methods = ["GET"])
def api_birds():
    try:
        dbConnection = db.connectDB()

        # ?limit and ?offset let React ask for a specific page. Defaults
        # (24, 0) cover the first request when React doesn't pass either.
        limit = request.args.get("limit", default=24, type=int)
        offset = request.args.get("offset", default=0, type=int)

        query1 = """
            SELECT Birds.*, GROUP_CONCAT(BirdPhotos.photographUrl SEPARATOR '||') AS photoUrls
            FROM Birds
            LEFT JOIN BirdPhotos ON BirdPhotos.birdID = Birds.birdID
            GROUP BY Birds.birdID
            ORDER BY Birds.birdID ASC
            LIMIT %s OFFSET %s;
        """

        birds = db.query(dbConnection, query1, (limit, offset)).fetchall()

        for bird in birds:
            raw_urls = bird.pop("photoUrls")
            bird["photos"] = raw_urls.split("||") if raw_urls else []

        # Total count (not just this page) so React knows whether a
        # "Load more" click would return anything
        total_count = db.query(dbConnection, "SELECT COUNT(*) AS total FROM Birds;").fetchone()["total"]

        return jsonify({
            "birds": birds,
            "hasMore": offset + len(birds) < total_count
        })

    except Exception as e:
        print(f"Error executing queries: {e}")
        return jsonify({"error": "An error occurred while executing the db queries."}), 500

    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Call to identify uploaded bird.
@app.route("/api/identify", methods=["POST"])
def identify_bird():
    try:
        img = None

        # Case 1: a file was uploaded. request.files["image"] only exists
        # if the frontend's <input name="image"> actually has a file
        # selected -- an empty file input still shows up with an empty
        # filename, so check that too.
        if "image" in request.files and request.files["image"].filename != "":
            uploaded_file = request.files["image"]
            img = Image.open(uploaded_file.stream)

        # Case 2: no file, so check for a URL field instead. This comes
        # through request.form since it's a regular text field, not a file.
        elif request.form.get("image_url"):
            image_url = request.form.get("image_url")
            # classify_image_from_url already does the fetch+open itself,
            # so we don't duplicate that logic here -- just call it
            # directly and skip the shared classify_image() call below.
            top_class, all_predictions = classify_image_from_url(image_url, top_k=5)
            results = [{"name": name, "confidence": confidence} for name, confidence in all_predictions]
            return jsonify({"results": results})

        # Neither a file nor a URL was provided.
        if img is None:
            return jsonify({"error": "No image file or image URL provided"}), 400

        top_class, all_predictions = classify_image(img, top_k=5)
        results = [{"name": name, "confidence": confidence} for name, confidence in all_predictions]

        return jsonify({"results": results})

    except Exception as e:
        print(f"Error running identification: {e}")
        return jsonify({"error": "An error occurred while identifying the bird."}), 500

############################################
########### ROUTE HANDLERSS ###########
############################################

############################################
# READ ROUTES
############################################

# Homepage
@app.route("/Avidex", methods = ["GET"])
def home():
    try:
        return render_template("home.j2")

    except Exception as e:
        print(f"Error rendering page: {e}")
        return f"An error occurred while rendering the page: {e}", 500

# Bird Page
@app.route("/Avidex/birds", methods = ["GET"])
def avidex_birds():
    try:
        dbConnection = db.connectDB() 

        # Creating and executing our queries
        query1 = "SELECT * FROM Birds ORDER BY Birds.birdID ASC;"
        query2 = "SELECT * FROM Rarities"

        birds = db.query(dbConnection, query1).fetchall()
        rarities = db.query(dbConnection, query2).fetchall()

        # Render the page and pass both the birds and rarities data to the template.
        return render_template(
            "birds.j2", birds = birds, rarities = rarities
        )

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500

    finally:
        # closing the DB connection, if it exists
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Bird Photos Page
@app.route("/Avidex/bird-photos", methods = ["GET"])
def avidex_bird_photos():
    try:
        dbConnection = db.connectDB()

        # Join so the template can show commonName instead of a bare birdID
        query1 = "SELECT BirdPhotos.photoID, Birds.commonName, BirdPhotos.photographUrl, BirdPhotos.license, BirdPhotos.artist FROM BirdPhotos\
                LEFT JOIN Birds ON Birds.birdID = BirdPhotos.birdID;"
        query2 = "SELECT * FROM Birds;"

        photos = db.query(dbConnection, query1).fetchall()
        birds = db.query(dbConnection, query2).fetchall()

        return render_template(
            "bird-photos.j2", photos = photos, birds = birds
        )

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500

    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()


# Bird Calls Page
@app.route("/Avidex/bird-calls", methods = ["GET"])
def avidex_bird_calls():
    try:
        dbConnection = db.connectDB()

        query1 = "SELECT BirdCalls.callID, Birds.commonName, BirdCalls.callUrl, BirdCalls.license, BirdCalls.recordist FROM BirdCalls\
                LEFT JOIN Birds ON Birds.birdID = BirdCalls.birdID;"
        query2 = "SELECT * FROM Birds;"

        calls = db.query(dbConnection, query1).fetchall()
        birds = db.query(dbConnection, query2).fetchall()

        return render_template(
            "bird-calls.j2", calls = calls, birds = birds
        )

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500

    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Rarity Page
@app.route("/Avidex/rarities", methods = ["GET"])
def avidex_rarities():
    try:
        dbConnection = db.connectDB()

        query1 = "SELECT * FROM Rarities;"

        rarities = db.query(dbConnection, query1).fetchall()

        return render_template(
            "rarities.j2", rarities = rarities
        )
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Birders Page
@app.route("/Avidex/birders", methods = ["GET"])
def avidex_birders():
    try:
        dbConnection = db.connectDB()

        query1 = "SELECT * FROM Birders;"

        birders = db.query(dbConnection, query1).fetchall()

        return render_template(
            "birders.j2", birders = birders
        )

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Nests Page
@app.route("/Avidex/nests", methods = ["GET"])
def avidex_nests():
    try:
        dbConnection = db.connectDB()

        query1 = "SELECT * FROM Nests;"

        nests = db.query(dbConnection, query1).fetchall()

        return render_template(
            "nests.j2", nests = nests
        )


    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Rewards Page
@app.route("/Avidex/rewards", methods = ["GET"])
def avidex_rewards():
    try:
        dbConnection = db.connectDB()

        query1 = "SELECT * FROM Rewards;"

        rewards = db.query(dbConnection, query1).fetchall()

        return render_template(
            "rewards.j2", rewards = rewards
        )


    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Sightings Page
@app.route("/Avidex/sightings", methods = ["GET"])
def avidex_sightings():
    try:
        dbConnection = db.connectDB()

        query1 = "SELECT Sightings.sightingID, Birders.birderName, Birds.commonName, Sightings.birdCount, ST_AsText(Sightings.gpsLocation) AS gpsLocation, Sightings.time FROM Sightings\
                LEFT JOIN Birders ON Birders.birderID = Sightings.birderID\
                LEFT JOIN Birds ON Birds.birdID = Sightings.birdID;"
        query2 = "SELECT * FROM Birders;"
        query3 = "SELECT * FROM Birds;"

        sightings = db.query(dbConnection, query1).fetchall()
        birders = db.query(dbConnection, query2).fetchall()
        birds = db.query(dbConnection, query3).fetchall()

        return render_template(
            "sightings.j2", sightings = sightings, birders = birders, birds = birds
        )


    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# BirdersRewards Page
@app.route("/Avidex/birders-rewards", methods = ["GET"])
def avidex_birders_rewards():
    try:
        dbConnection = db.connectDB()

        query1 = "SELECT BirdersRewards.birderID, Birders.birderName, BirdersRewards.rewardID, Rewards.name AS rewardName FROM BirdersRewards\
                LEFT JOIN Birders ON Birders.birderID = BirdersRewards.birderID\
                LEFT JOIN Rewards ON Rewards.rewardID = BirdersRewards.rewardID;"
        query2 = "SELECT * FROM Birders;"
        query3 = "SELECT * FROM Rewards;"

        birdersrewards = db.query(dbConnection, query1).fetchall()
        birders = db.query(dbConnection, query2).fetchall()
        rewards = db.query(dbConnection, query3).fetchall()

        return render_template(
            "birders-rewards.j2", birdersrewards = birdersrewards, birders = birders, rewards = rewards
        )
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# BirdsList Page
@app.route("/Avidex/bird-totals", methods = ["GET"])
def avidex_birds_list():
    try:
        dbConnection = db.connectDB()

        query1 = "SELECT * FROM v_bird_totals;"
        query2 = "SELECT * FROM Birders;"
        query3 = "SELECT * FROM Birds;"

        birdslists = db.query(dbConnection, query1).fetchall()
        birders = db.query(dbConnection, query2).fetchall()
        birds = db.query(dbConnection, query3).fetchall()

        return render_template(
            "bird-totals.j2", birdslists = birdslists, birders = birders, birds = birds
        )
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# BirdsNests Page
@ app.route("/Avidex/birds-nests", methods = ["GET"])
def avidex_birds_nests():
    try:
        dbConnection = db.connectDB()

        query1 = "SELECT Birds.birdID, Birds.commonName, BirdsNests.nestID, Nests.type, Nests.location FROM BirdsNests\
                LEFT JOIN Birds ON Birds.birdID = BirdsNests.birdID\
                LEFT JOIN Nests ON Nests.nestID = BirdsNests.nestID;"
        query2 = "SELECT * FROM Birds;"
        query3 = "SELECT * FROM Nests;"

        birdsnests = db.query(dbConnection, query1).fetchall()
        birds = db.query(dbConnection, query2).fetchall()
        nests = db.query(dbConnection, query3).fetchall()

        return render_template(
            "birds-nests.j2", birdsnests = birdsnests, birds = birds, nests = nests
        )

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()










############################################
# POST ROUTES
############################################

# Reset Button
@app.route("/Avidex/reset", methods = ["POST"])
def reset_db_route():
    try:
        dbConnection = db.connectDB()
        db.query(dbConnection, "CALL pl_reset_avidex();")

        os.system("pwd")

        next_url = request.form.get("next") or request.referrer or "/Avidex"
        
        return redirect(next_url)
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()









#################################
# ADD OBJECT
#################################

# Add a Birder
@app.route("/Avidex/birders/create", methods = ["POST"])
def add_birder():
    try:
        dbConnection = db.connectDB()

        birder_name = request.form.get("create_birder_name")
        birder_points = int(request.form.get("create_birder_points"))

        db.query(dbConnection, "CALL pl_add_birder(%s,%s);",(birder_name, birder_points))
        
        return redirect("/Avidex/birders")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Add a Bird
@app.route("/Avidex/birds/create", methods = ["POST"])
def add_bird():
    try:
        dbConnection = db.connectDB()

        bird_rarity = request.form.get("create_bird_rarity")
        bird_commonName = request.form.get("create_bird_common_name")
        bird_species = request.form.get("create_bird_species")
        bird_callUrl = request.form.get("create_bird_call_url")
        bird_wingspan = request.form.get("create_bird_wingspan")
        bird_size = request.form.get("create_bird_size")
        bird_identifyingMarks = request.form.get("create_bird_identifying_marks")
        bird_range = request.form.get("create_bird_range")
        bird_description = request.form.get("create_bird_description")
        bird_photographUrl = request.form.get("create_bird_photograph_url")
        bird_matingSeason = request.form.get("create_bird_mating_season")

        db.query(dbConnection, "CALL pl_add_bird(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);", (
            bird_rarity,
            bird_commonName,
            bird_species,
            bird_callUrl,
            bird_wingspan,
            bird_size,
            bird_identifyingMarks,
            bird_range,
            bird_description,
            bird_photographUrl,
            bird_matingSeason
        ))

        return redirect("/Avidex/birds")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Add a Bird Photo
@app.route("/Avidex/bird-photos/create", methods = ["POST"])
def add_bird_photo():
    try:
        dbConnection = db.connectDB()

        birdID = int(request.form.get("create_photo_bird"))
        url = request.form.get("create_photo_url")
        license_ = request.form.get("create_photo_license")  # "license" shadows a Python builtin, hence the trailing underscore
        artist = request.form.get("create_photo_artist")

        db.query(dbConnection, "CALL pl_add_bird_photo(%s,%s,%s,%s);",(birdID, url, license_, artist))

        return redirect("/Avidex/bird-photos")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500

    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()


# Add a Bird Call
@app.route("/Avidex/bird-calls/create", methods = ["POST"])
def add_bird_call():
    try:
        dbConnection = db.connectDB()

        birdID = int(request.form.get("create_call_bird"))
        url = request.form.get("create_call_url")
        license_ = request.form.get("create_call_license")
        recordist = request.form.get("create_call_recordist")

        db.query(dbConnection, "CALL pl_add_bird_call(%s,%s,%s,%s);",(birdID, url, license_, recordist))

        return redirect("/Avidex/bird-calls")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500

    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Add a Reward
@app.route("/Avidex/rewards/create", methods = ["POST"])
def add_reward():
    try:
        dbConnection = db.connectDB()

        reward_name = request.form.get("create_reward_name")
        reward_description = request.form.get("create_reward_description")
        reward_threshold = int(request.form.get("create_reward_threshold"))

        db.query(dbConnection, "CALL pl_add_reward(%s,%s,%s);",(reward_name,reward_description,reward_threshold))

        return redirect("/Avidex/rewards")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Add a Birder's Reward
@app.route("/Avidex/birders-rewards/create", methods = ["POST"])
def add_birders_reward():
    try:
        dbConnection = db.connectDB()

        rewardID = request.form.get("create_birderreward_reward_name")
        birderID = request.form.get("create_birderreward_birder_name")

        db.query(dbConnection, "CALL pl_add_birder_reward(%s,%s);",(birderID, rewardID))

        return redirect("/Avidex/birders-rewards")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Add a Bird's Nest
@app.route("/Avidex/birds-nests/create", methods = ["POST"])
def add_birds_nest():
    try:
        dbConnection = db.connectDB()

        birdID = int(request.form.get("create_birdnest_bird"))
        nestID = int(request.form.get("create_birdnest_nest"))

        db.query(dbConnection, "CALL pl_add_birds_nest(%s,%s);",(birdID,nestID))

        return redirect("/Avidex/birds-nests")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Add a Nest
@app.route("/Avidex/nests/create", methods = ["POST"])
def add_nest():
    try:
        dbConnection = db.connectDB()

        nest_type = request.form.get("create_nest_type")
        nest_location = request.form.get("create_nest_location")

        db.query(dbConnection, "CALL pl_add_nest(%s,%s);",(nest_type, nest_location))

        return redirect("/Avidex/nests")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()
 
# Add a Rarity
@app.route("/Avidex/rarities/create", methods = ["POST"])
def add_rarity():
    try:
        dbConnection = db.connectDB()

        rarity = request.form.get("create_rarity")

        db.query(dbConnection, "CALL pl_add_rarity(%s);",(rarity,))

        return redirect("/Avidex/rarities")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Add a Sighting
@app.route("/Avidex/sightings/create", methods = ["POST"])
def add_sightings():
    try:
        dbConnection = db.connectDB()
        print("DB is connected", dbConnection)

        birderID = int(request.form.get("create_sighting_birder"))
        birdID = int(request.form.get("create_sighting_bird"))
        count = int(request.form.get("create_sighting_bird_count"))
        latitude = float(request.form.get("create_sighting_latitude"))
        longitude = float(request.form.get("create_sighting_longitude"))
        time = request.form.get("create_sighting_time", "").strip()

        if time == "":
            time = None


        db.query(dbConnection, "CALL pl_add_sighting(%s,%s,%s,ST_SRID(POINT(%s,%s),4326),%s);",(birderID,birdID, count, longitude, latitude, time))

        return redirect("/Avidex/sightings")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()













#################################
# UPDATE OBJECT
#################################

# Update a Birder
@app.route("/Avidex/birders/update", methods = ["POST"])
def update_birder():
    try:
        dbConnection = db.connectDB()

        birder = int(request.form.get("update_birder"))
        name = request.form.get("update_birder_name")
        points = int(request.form.get("update_birder_points"))

        db.query(dbConnection, "CALL pl_update_birder(%s,%s,%s);",(birder, name, points))
        
        return redirect("/Avidex/birders")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Update a Bird
@app.route("/Avidex/birds/update", methods = ["POST"])
def update_bird():
    try:
        dbConnection = db.connectDB()

        bird_birdID = int(request.form.get("update_bird_id"))
        bird_rarity = request.form.get("update_bird_rarity")
        bird_commonName = request.form.get("update_bird_common_name")
        bird_species = request.form.get("update_bird_species")
        bird_callUrl = request.form.get("update_bird_call_url")
        bird_wingspan = request.form.get("update_bird_wingspan")
        bird_size = request.form.get("update_bird_size")
        bird_identifyingMarks = request.form.get("update_bird_identifying_marks")
        bird_range = request.form.get("update_bird_range")
        bird_description = request.form.get("update_bird_description")
        bird_photographUrl = request.form.get("update_bird_photograph_url")
        bird_matingSeason = request.form.get("update_bird_mating_season")

        db.query(dbConnection, "CALL pl_update_bird(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);", (
            bird_birdID,
            bird_rarity,
            bird_commonName,
            bird_species,
            bird_callUrl,
            bird_wingspan,
            bird_size,
            bird_identifyingMarks,
            bird_range,
            bird_description,
            bird_photographUrl,
            bird_matingSeason
        ))

        return redirect("/Avidex/birds")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Update a Reward
@app.route("/Avidex/rewards/update", methods = ["POST"])
def update_reward():
    try:
        dbConnection = db.connectDB()

        reward_rewardID = int(request.form.get("update_reward"))
        reward_name = request.form.get("update_reward_name")
        reward_description = request.form.get("update_reward_description")
        reward_threshold = int(request.form.get("update_reward_threshold"))

        db.query(dbConnection, "CALL pl_update_reward(%s,%s,%s,%s);",(reward_rewardID, reward_name,reward_description,reward_threshold))

        return redirect("/Avidex/rewards")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Update a Birder's Reward
@app.route("/Avidex/birders-rewards/update", methods = ["POST"])
def update_birders_reward():
    try:
        dbConnection = db.connectDB()

        oldBirderID = request.form.get("update_birderreward_old_birder_id")
        oldRewardID = request.form.get("update_birderreward_old_reward_id")
        newBirderID = request.form.get("update_birderreward_new_birder_id")
        newRewardID = request.form.get("update_birderreward_new_reward_id")

        db.query(dbConnection, "CALL pl_update_birder_reward(%s,%s,%s,%s);",(
            oldBirderID,
            oldRewardID,
            newBirderID,
            newRewardID
        ))

        return redirect("/Avidex/birders-rewards")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Update a Bird's Nest
@app.route("/Avidex/birds-nests/update", methods = ["POST"])
def update_birds_nest():
    try:
        dbConnection = db.connectDB()

        oldBirdID = int(request.form.get("update_birdnest_old_bird"))
        oldNestID = int(request.form.get("update_birdnest_old_nest"))
        newBirdID = int(request.form.get("update_birdnest_new_bird"))
        newNestID = int(request.form.get("update_birdnest_new_nest"))
        

        db.query(dbConnection, "CALL pl_update_bird_nest(%s,%s,%s,%s);",(
            oldBirdID,
            oldNestID,
            newBirdID,
            newNestID
        ))

        return redirect("/Avidex/birds-nests")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Update a Nest
@app.route("/Avidex/nests/update", methods = ["POST"])
def update_nest():
    try:
        dbConnection = db.connectDB()

        nest_nestID = int(request.form.get("update_nest"))
        nest_type = request.form.get("update_nest_type")
        nest_location = request.form.get("update_nest_location")

        db.query(dbConnection, "CALL pl_update_nest(%s,%s,%s);",(
            nest_nestID,
            nest_type,
            nest_location
        ))

        return redirect("/Avidex/nests")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()
 
# Update a Rarity
@app.route("/Avidex/rarities/update", methods = ["POST"])
def update_rarity():
    try:
        dbConnection = db.connectDB()

        oldRarity = request.form.get("update_oldRarity")
        newRarity = request.form.get("update_newRarity")

        db.query(dbConnection, "CALL pl_update_rarity(%s,%s);",(oldRarity,newRarity))

        return redirect("/Avidex/rarities")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Update a Sighting
@app.route("/Avidex/sightings/update", methods = ["POST"])
def update_sightings():
    try:
        dbConnection = db.connectDB()

        sightingID = int(request.form.get("update_sighting"))
        birderID = int(request.form.get("update_sighting_birder"))
        birdID = int(request.form.get("update_sighting_bird"))
        count = int(request.form.get("update_sighting_bird_count"))
        location = request.form.get("update_sighting_gps_location") or None
        time = request.form.get("update_sighting_time") or None


        db.query(dbConnection, "CALL pl_update_sighting(%s,%s,%s,%s,%s,%s);",(
            sightingID,
            birderID,
            birdID,
            count,
            location,
            time
        ))

        return redirect("/Avidex/sightings")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()


# Update a BirdPhoto
@app.route("/Avidex/bird-photos/update", methods = ["POST"])
def update_bird_photo():
    try:
        dbConnection = db.connectDB()

        photoID = int(request.form.get("update_photo"))
        birdID = int(request.form.get("update_photo_bird"))
        url = request.form.get("update_photo_url")
        license = request.form.get("update_photo_license")
        artist = request.form.get("update_photo_artist")

        db.query(dbConnection, "CALL pl_update_bird_photo(%s,%s,%s,%s,%s);",(
            photoID,
            birdID,
            url,
            license,
            artist
        ))

        return redirect("/Avidex/bird-photos")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()


# Update a BirdCall
@app.route("/Avidex/bird-calls/update", methods = ["POST"])
def update_bird_call():
    try:
        dbConnection = db.connectDB()

        callID = int(request.form.get("update_call"))
        birdID = int(request.form.get("update_call_bird"))
        url = request.form.get("update_call_url")
        license = request.form.get("update_call_license")
        recordist = request.form.get("update_call_recordist")

        db.query(dbConnection, "CALL pl_update_bird_call(%s,%s,%s,%s,%s);",(
            callID,
            birdID,
            url,
            license,
            recordist
        ))

        return redirect("/Avidex/bird-calls")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()






#################################
# DELETE OBJECT
#################################

# Delete a Bird
@app.route("/Avidex/birds/delete", methods=["POST"])
def delete_bird():
    try:
        dbConnection = db.connectDB()

        birdID = int(request.form.get("delete_bird_id"))

        db.query(dbConnection, "CALL pl_delete_bird(%s);",(birdID,))

        return redirect("/Avidex/birds")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Delete a Birder
@app.route("/Avidex/birders/delete", methods = ["POST"])
def delete_birder():
    try:
        dbConnection = db.connectDB()

        birder = int(request.form.get("delete_birder_id"))

        db.query(dbConnection, "CALL pl_delete_birder(%s);",(birder,))
        
        return redirect("/Avidex/birders")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Delete a Reward
@app.route("/Avidex/rewards/delete", methods = ["POST"])
def delete_reward():
    try:
        dbConnection = db.connectDB()

        reward = int(request.form.get("delete_reward_id"))

        db.query(dbConnection, "CALL pl_delete_reward(%s);",(reward,))

        return redirect("/Avidex/rewards")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Delete a Birder's Reward
@app.route("/Avidex/birders-rewards/delete", methods = ["POST"])
def delete_birders_reward():
    try:
        dbConnection = db.connectDB()

        birderID = int(request.form.get("delete_birderreward_birderID"))
        rewardID = int(request.form.get("delete_birderreward_rewardID"))

        db.query(dbConnection, "CALL pl_delete_birder_reward(%s,%s)",(birderID,rewardID))

        return redirect("/Avidex/birders-rewards")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Delete a Bird's Nest
@app.route("/Avidex/birds-nests/delete", methods = ["POST"])
def delete_birds_nest():
    try:
        dbConnection = db.connectDB()

        birdID = int(request.form.get("delete_birdnest_birdID"))
        nestID = int(request.form.get("delete_birdnest_nestID"))
        

        db.query(dbConnection, "CALL pl_delete_bird_nest(%s,%s);",(birdID,nestID))

        return redirect("/Avidex/birds-nests")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Delete a Nest
@app.route("/Avidex/nests/delete", methods = ["POST"])
def delete_nest():
    try:
        dbConnection = db.connectDB()

        nestID = int(request.form.get("delete_nest_id"))

        db.query(dbConnection, "CALL pl_delete_nest(%s);",(nestID,))

        return redirect("/Avidex/nests")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()
 
# Delete a Rarity
@app.route("/Avidex/rarities/delete", methods = ["POST"])
def delete_rarity():
    try:
        dbConnection = db.connectDB()

        rarity = request.form.get("delete_rarity")

        db.query(dbConnection, "CALL pl_delete_rarity(%s);",(rarity,))

        return redirect("/Avidex/rarities")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Delete a Sighting
@app.route("/Avidex/sightings/delete", methods = ["POST"])
def delete_sightings():
    try:
        dbConnection = db.connectDB()

        sighting = int(request.form.get("delete_sighting_id"))

        db.query(dbConnection, "CALL pl_delete_sighting(%s);",(sighting,))

        return redirect("/Avidex/sightings")
    
    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500
    
    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

# Delete a Bird Photo
@app.route("/Avidex/bird-photos/delete", methods = ["POST"])
def delete_bird_photo():
    try:
        dbConnection = db.connectDB()

        photoID = int(request.form.get("delete_photo_id"))

        db.query(dbConnection, "CALL pl_delete_bird_photo(%s);",(photoID,))

        return redirect("/Avidex/bird-photos")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500

    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()


# Delete a Bird Call
@app.route("/Avidex/bird-calls/delete", methods = ["POST"])
def delete_bird_call():
    try:
        dbConnection = db.connectDB()

        callID = int(request.form.get("delete_call_id"))

        db.query(dbConnection, "CALL pl_delete_bird_call(%s);",(callID,))

        return redirect("/Avidex/bird-calls")

    except Exception as e:
        print(f"Error executing queries: {e}")
        return f"An error occurred while executing the db queries: {e}", 500

    finally:
        if "dbConnection" in locals() and dbConnection: dbConnection.close()

#################################
########### LISTENER ###########
#################################
if __name__ == "__main__":
    app.run(
        port = PORT, debug = True
    )