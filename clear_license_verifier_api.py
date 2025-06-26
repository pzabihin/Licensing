from flask import Flask, request, jsonify, send_file
import pandas as pd
import tempfile
import os

# Load unified license verification data
try:
    df_licenses = pd.read_excel("Unified_License_Verification_Result.xlsx")
except Exception as e:
    df_licenses = pd.DataFrame()
    print("⚠️ WARNING: Could not load license data:", e)

app = Flask(__name__)

def lookup_provider(provider_name, state):
    state = state.upper()
    row = df_licenses[df_licenses["Provider Name"].str.lower() == provider_name.lower()]
    if row.empty:
        return {"provider": provider_name, "state": state, "status": "No record found"}

    licensed_col = f"{state} Licensed?"
    summary_col = f"{state} Summary"

    if licensed_col in row.columns:
        return {
            "provider": provider_name,
            "state": state,
            "licensed": row.iloc[0][licensed_col],
            "summary": row.iloc[0][summary_col]
        }
    else:
        return {"provider": provider_name, "state": state, "status": "State not supported"}

@app.route('/verify', methods=['POST'])
def verify():
    data = request.get_json()
    provider = data.get('provider_name')
    state = data.get('state')
    if not provider or not state:
        return jsonify({"error": "Missing provider_name or state"}), 400
    result = lookup_provider(provider, state)
    return jsonify(result)

@app.route('/batch', methods=['POST'])
def batch():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    try:
        df_input = pd.read_excel(file)
    except Exception as e:
        return jsonify({"error": f"Unable to read Excel file: {str(e)}"}), 400

    if 'Provider Name' not in df_input.columns or 'Target Campaign State' not in df_input.columns:
        return jsonify({"error": "Excel must include 'Provider Name' and 'Target Campaign State' columns."}), 400

    results = []
    for _, row in df_input.iterrows():
        name = row.get("Provider Name", "")
        state = row.get("Target Campaign State", "")
        results.append(lookup_provider(name, state))

    df_results = pd.DataFrame(results)
    if df_results.empty:
        return jsonify({"error": "No valid provider results generated."}), 400

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df_results.to_excel(temp_file.name, index=False)

    return send_file(temp_file.name, as_attachment=True, download_name="Batch_License_Verification_Results.xlsx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
