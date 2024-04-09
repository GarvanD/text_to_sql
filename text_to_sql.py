import sqlite3
import json
import anthropic
from anthropic import AnthropicBedrock

# Initialize the Anthropic client
# client = anthropic.AnthropicBedrock()  # Uncomment this line if using AnthropicBedrock
client = anthropic.Anthropic()

# Read the prompt template from prompt.txt
with open("prompt.txt") as f:
    prompt = f.read()

# Read the database schema from schema.txt
with open("schema.txt") as f:
    schema = f.read()

def run_query(query, db_path="./demo.sqlite"):
    """
    Execute an SQL query against the specified SQLite database.
    
    Args:
        query (str): The SQL query to execute.
        db_path (str): The path to the SQLite database file.
    
    Returns:
        list: The rows returned by the query.
    """
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Execute the SQL query
        cursor.execute(query)

        # Fetch all the rows returned by the query
        rows = cursor.fetchall()

        # Get the column names from the cursor description
        column_names = [description[0] for description in cursor.description]

        # Print the column names
        print(", ".join(column_names))

        # Print the rows
        for row in rows:
            print(", ".join(str(value) for value in row))

        return rows

    except sqlite3.Error as e:
        print(f"Error executing query: {e}")

    finally:
        # Close the cursor and the database connection
        cursor.close()
        conn.close()

def generate_query(query, similar=[], verbose=False):
    """
    Generate an SQL query based on a natural language question using an LLM.
    
    Args:
        query (str): The natural language question.
        similar (list): A list of similar questions and their corresponding SQL queries.
        verbose (bool): Whether to print verbose output.
    
    Returns:
        str: The generated SQL query.
    """
    # Replace placeholders in the prompt template with actual values
    replaced_prompt = (
        prompt.replace("{$SCHEMA}", schema)
        .replace("{$QUESTION}", query)
        .replace("{$DATABASE_TYPE}", "sqlite")
        .replace("{$SIMILAR_QUERIES}", json.dumps(similar, indent=4))
    )
    
    # Send the prompt to the LLM and receive the response
    result = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": replaced_prompt},
            {"role": "assistant", "content": "<response>"}, # Ensuring the response starts with "<response>" 
        ],
        stop_sequences=["</response>"], # Using prompt output schema as end sequence (see prompt.txt)
    )
    
    # Extract the generated SQL query from the LLM response
    sql = result.content[0].text.split("<sql>")[1].split("</sql>")[0]
    
    if verbose:
        print("Prompt")
        print(replaced_prompt)
        print("\n\n\n\n")
        print("Chain of thought")
        print(
            "<scratchpad>"
            + result.content[0].text.split("<scratchpad>")[1].split("</feedback>")[0]
            + "</feedback>"
        )
        print("\n\n\n\n")
        print("SQL")
        print(sql)
    
    return sql

# Example usage
query = "What is the most popular genre by sales?"
similar = [
    {
        "question": "What is the most popular media type by sales?",
        "sql": "SELECT media_types.Name AS MediaType, SUM(invoice_items.Quantity * invoice_items.UnitPrice) AS TotalSales FROM media_types JOIN tracks ON media_types.MediaTypeId = tracks.MediaTypeId JOIN invoice_items ON tracks.TrackId = invoice_items.TrackId GROUP BY media_types.MediaTypeId ORDER BY TotalSales DESC LIMIT 1",
    },
    {
        "question": "What is the most popular artist by number of tracks sold?",
        "sql": "SELECT artists.Name AS Artist, SUM(invoice_items.Quantity) AS TracksSold FROM artists JOIN albums ON artists.ArtistId = albums.ArtistId JOIN tracks ON albums.AlbumId = tracks.AlbumId JOIN invoice_items ON tracks.TrackId = invoice_items.TrackId GROUP BY artists.ArtistId ORDER BY TracksSold DESC LIMIT 1",
    },
    {
        "question": "What is the most popular album by revenue generated?",
        "sql": "SELECT albums.Title AS Album, SUM(invoice_items.Quantity * invoice_items.UnitPrice) AS Revenue FROM albums JOIN tracks ON albums.AlbumId = tracks.AlbumId JOIN invoice_items ON tracks.TrackId = invoice_items.TrackId GROUP BY albums.AlbumId ORDER BY Revenue DESC LIMIT 1",
    },
    {
        "question": "What is the most popular playlist by total duration of tracks?",
        "sql": "SELECT playlists.Name AS Playlist, SUM(tracks.Milliseconds) AS TotalDuration FROM playlists JOIN playlist_track ON playlists.PlaylistId = playlist_track.PlaylistId JOIN tracks ON playlist_track.TrackId = tracks.TrackId GROUP BY playlists.PlaylistId ORDER BY TotalDuration DESC LIMIT 1",
    },
]

# Generate SQL query based on the natural language question
sql = generate_query(query, similar, verbose=True)

# Run the generated SQL query
result = run_query(sql)
