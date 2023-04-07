from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
import textwrap
import re
import json
import requests
import openai
import psycopg2

app = Flask(__name__)


# Initialize the API client with your API key
openai.api_key = "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"

# Replace the values below with your actual database connection information
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://crowtech:testicles@77.68.97.97:5432/experimental"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    text = data.get('text')
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are Samantha, if asked about yourself you can gerenate whatever backstory you want. You do not know what OpenAI is or ChatGPT or GPT Models. You can help with any business qusetions. you action requests onto the crowtech BDM system, crowtech BDM is a living database for any type of business and is felxible enough to add any type of business data. when asked what are you?, you answer with this 'I am your AI business assitant created by crowtech to handle all of your business data and to help you suceed. asky me anything' "},
            {"role": "user", "content": text}
      

        ]
    )
    message = completion.choices[0].message
    return jsonify({'message': message})



@app.route('/tag_input', methods=['POST'])
def tag_input():
    data = request.get_json()
    text = data.get('text')
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0301",
        messages=[
            {"role": "system", "content": "Your only responsibility is to extract the intent and entities from a request. If there is no entities to extract just respond with the intent and nothing else like this example 'Intent: add a new cake recipe' "},
            {"role": "user", "content": text}

        ]
    )


    message= completion.choices[0].message
    return jsonify({'message': message})







@app.route('/extract_intent', methods=['POST'])
def extract_intent():
    data = request.get_json()
    text = data.get('text')
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0301",
        messages=[
            {"role": "system", "content": "You are an NLP Generative model, extract the intent from this input:"},
            {"role": "user", "content": text}

        ]
    )


    message= completion.choices[0].message
    return jsonify({'message': message})


@app.route('/generate_questions', methods=['POST'])
def generate_questions():
    data = request.get_json()
    text = data.get('text')
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0301",
        messages=[
            {"role": "system", "content": "You are a CRM AI that requires details for the given intent to fulfil the action, suggest 4 details required to complete action"},
            {"role": "user", "content": text}

        ]
    )


    message= completion.choices[0].message
    return jsonify({'message': message})



@app.route('/extract_entities', methods=['POST'])
def extract_entities():
    data = request.get_json()
    text = data.get('text')
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0301",
        messages=[
            {"role": "system", "content": "You are an NLP Generative model, you only extract entities. Only reespond with the extracted entities and thier values in this format: {entity name}: {entity value} "},
            {"role": "user", "content": text}

        ]
    )


    message= completion.choices[0].message
    return jsonify({'message': message})

def get_database_schema(engine):
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    metadata = MetaData()
    metadata.reflect(engine)

    table_strings = []

    for table_name in table_names:
        table = metadata.tables[table_name]
        columns = table.columns
        example_row = engine.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchone()

        column_strings = []
        for column in columns:
            example_value = example_row[column.name] if example_row else "N/A"
            column_strings.append(f"  {column.name} {column.type} {'NULL' if column.nullable else 'NOT NULL'}; Example: {example_value}")

        table_string = (
            "CREATE TABLE " + table_name + " (\n" +
            ',\n'.join(column_strings) +
            "\n);"
        )
        table_strings.append(table_string)

    return "\n\n".join(table_strings)



def generate_sql(schema_info=None):
    data = request.get_json()
    text = data.get('text')
    system_message = textwrap.dedent(f"You are an SQL Query generator. Generate a valid formatted SQL query for a database with the following schema information: {schema_info}. Here's the user input: {text}.") + " You can use the '%' wildcard with the LIKE operator to search for partial matches.not other text to be written apart from the query, wrap query in  %%% %%%"
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0301",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": text}
        ]
    )

    response = completion.choices[0].message.content.strip()
    print(response)
    queries = extract_queries_from_response(response)

    results = []
    for query in queries:
        try:
            # Execute SQL query and fetch results
            result = db.engine.execute(query)
            rows = [dict(row) for row in result]

            results.append({"query": query, "result": rows, "error": None})
        except Exception as e:
            results.append({"query": query, "result": None, "error": str(e)})

    return jsonify({"results": results})


def extract_queries_from_response(response_content: str):
    # You can use a simple regex to extract queries from the response content
    import re
    matches = re.findall(r'%%%\s*([^`]+)\s*%%%', response_content, re.MULTILINE)
    return matches




if __name__ == "__main__":
    with app.app_context():
        schema_info = get_database_schema(db.engine)
        app.add_url_rule('/generate_sql', 'generate_sql', lambda: generate_sql(schema_info=schema_info), methods=['POST'])
    app.run(host='77.68.97.97', port=5432, debug=True)
