import logging
import math
import re
import warnings
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from bson import ObjectId
from flask import Flask, current_app, jsonify, render_template, request
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from config import Config
from database.mongodb import get_predictions_collection

EXPECTED_FEATURES = [
    "job_title",
    "country",
    "experience_level",
    "years_experience",
    "skills_python",
    "skills_sql",
    "skills_ml",
    "skills_deep_learning",
    "skills_cloud",
]
SKILL_FIELDS = {
    "python": "skills_python",
    "sql": "skills_sql",
    "machineLearning": "skills_ml",
    "deepLearning": "skills_deep_learning",
    "cloud": "skills_cloud",
}
EXPERIENCE_ALIASES = {
    "EN": "Entry",
    "MI": "Mid",
    "SE": "Senior",
    "EX": "Executive",
    "Entry": "Entry",
    "Mid": "Mid",
    "Senior": "Senior",
    "Executive": "Executive",
}
EXPERIENCE_ORDER = ["Entry", "Mid", "Senior", "Executive"]
SKILLS = [
    ("Python", "skills_python"),
    ("SQL", "skills_sql"),
    ("Machine Learning", "skills_ml"),
    ("Deep Learning", "skills_deep_learning"),
    ("Cloud Computing", "skills_cloud"),
]


class InputError(ValueError):
    """Raised when a prediction request does not match the supported form."""


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    data = pd.read_csv(path)
    required = set(EXPECTED_FEATURES + ["salary", "job_openings"])
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    if data.empty:
        raise ValueError("The job market dataset contains no records.")

    for column in ["salary", "years_experience", "job_openings", *[c for _, c in SKILLS]]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["salary", "job_title", "country", "experience_level"])
    if data.empty:
        raise ValueError("The job market dataset has no usable salary records.")
    return data


@lru_cache(maxsize=4)
def _load_model(model_path: str):
    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(f"Trained salary model not found: {path}")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = joblib.load(path)
    warning_messages = sorted({str(warning.message) for warning in caught})
    for message in warning_messages:
        logging.getLogger(__name__).warning("Model loading warning: %s", message)

    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is None or list(feature_names) != EXPECTED_FEATURES:
        raise ValueError(
            "The trained model input columns do not match the supported salary form."
        )

    # Older saved pipelines use this attribute, renamed in newer scikit-learn.
    imputer = model.named_steps["preprocessor"].named_transformers_["num"]
    if hasattr(imputer, "_fit_dtype") and not hasattr(imputer, "_fill_dtype"):
        imputer._fill_dtype = imputer._fit_dtype
    return model


def get_model():
    return _load_model(str(current_app.config["MODEL_PATH"]))


def _counts(data: pd.DataFrame, column: str, limit: int = 10):
    values = data[column].value_counts().head(limit)
    return {"labels": values.index.astype(str).tolist(), "values": values.astype(int).tolist()}


def _salary_histogram(salaries: pd.Series):
    counts, edges = np.histogram(salaries.to_numpy(dtype=float), bins=8)
    labels = [
        f"{edges[index]:,.0f} - {edges[index + 1]:,.0f}"
        for index in range(len(counts))
    ]
    return {"labels": labels, "values": counts.astype(int).tolist()}


def build_analytics(data: pd.DataFrame):
    salaries = data["salary"].dropna()
    skill_demand = []
    for label, column in SKILLS:
        count = int(pd.to_numeric(data[column], errors="coerce").fillna(0).gt(0).sum())
        skill_demand.append(
            {
                "skill": label,
                "count": count,
                "percentage": round(count / len(data) * 100, 1),
            }
        )
    skill_demand.sort(key=lambda item: item["count"], reverse=True)

    salary_by_country = (
        data.groupby("country", observed=True)["salary"]
        .mean()
        .sort_values(ascending=False)
    )
    postings_by_country = data["country"].value_counts()
    openings_by_country = (
        data.groupby("country", observed=True)["job_openings"]
        .sum(min_count=1)
        .fillna(0)
        .sort_values(ascending=False)
    )

    experience_salary = (
        data.groupby("experience_level", observed=True)["salary"]
        .mean()
        .reindex([level for level in EXPERIENCE_ORDER if level in data["experience_level"].unique()])
        .dropna()
    )
    experience_counts = data["experience_level"].value_counts()
    ordered_experience = [
        level for level in EXPERIENCE_ORDER if level in experience_counts.index
    ]

    roles = _counts(data, "job_title")
    top_languages = [
        {
            "skill": item["skill"],
            "demand": item["count"],
            "percentage": item["percentage"],
        }
        for item in skill_demand
    ]

    return {
        "stats": {
            "jobPostings": int(len(data)),
            "jobRoles": int(data["job_title"].nunique()),
            "countries": int(data["country"].nunique()),
            "averageSalary": round(float(salaries.mean()), 2),
            "highestSalary": round(float(salaries.max()), 2),
            "lowestSalary": round(float(salaries.min()), 2),
            "totalOpenings": int(data["job_openings"].fillna(0).sum()),
            "salaryUnit": "Source dataset units; no currency column is provided.",
        },
        "topRoles": roles,
        "skillDemand": {
            "labels": [item["skill"] for item in skill_demand],
            "values": [item["count"] for item in skill_demand],
            "details": skill_demand,
        },
        "salaryDistribution": _salary_histogram(salaries),
        "salaryByCountry": {
            "labels": salary_by_country.index.astype(str).tolist(),
            "values": salary_by_country.round(2).tolist(),
            "postings": [
                int(postings_by_country.get(country, 0))
                for country in salary_by_country.index
            ],
        },
        "experienceSalary": {
            "labels": experience_salary.index.astype(str).tolist(),
            "values": experience_salary.round(2).tolist(),
        },
        "topLanguages": top_languages,
        "topProgrammingLanguages": [
            item for item in top_languages if item["skill"] in {"Python", "SQL"}
        ],
        "opportunitiesByCountry": {
            "labels": openings_by_country.index.astype(str).tolist(),
            "values": openings_by_country.astype(int).tolist(),
        },
        "experienceDistribution": {
            "labels": ordered_experience,
            "values": [int(experience_counts[level]) for level in ordered_experience],
        },
        "categories": {
            "jobRoles": sorted(data["job_title"].dropna().astype(str).unique().tolist()),
            "countries": sorted(data["country"].dropna().astype(str).unique().tolist()),
            "experienceLevels": [
                {"code": "EN", "label": "Entry"},
                {"code": "MI", "label": "Mid"},
                {"code": "SE", "label": "Senior"},
                {"code": "EX", "label": "Executive"},
            ],
            "minYearsExperience": int(data["years_experience"].min()),
            "maxYearsExperience": int(data["years_experience"].max()),
        },
    }


def _validate_prediction(payload, data: pd.DataFrame):
    if not isinstance(payload, dict):
        raise InputError("Send prediction details as a JSON object.")

    role = payload.get("jobRole")
    country = payload.get("country")
    experience = payload.get("experienceLevel")
    if not isinstance(role, str) or role not in set(data["job_title"].astype(str)):
        raise InputError("Choose a job role present in the training dataset.")
    if not isinstance(country, str) or country not in set(data["country"].astype(str)):
        raise InputError("Choose a country present in the training dataset.")
    if not isinstance(experience, str) or experience not in EXPERIENCE_ALIASES:
        raise InputError("Experience level must be EN, MI, SE, or EX.")

    years = payload.get("yearsExperience")
    if isinstance(years, bool) or not isinstance(years, (int, float)):
        raise InputError("Years of experience must be a number.")
    if not math.isfinite(years):
        raise InputError("Years of experience must be a finite number.")
    minimum = int(data["years_experience"].min())
    maximum = int(data["years_experience"].max())
    if years < minimum or years > maximum:
        raise InputError(f"Years of experience must be between {minimum} and {maximum}.")

    skills = payload.get("skills")
    if not isinstance(skills, dict):
        raise InputError("Provide all five technical skill selections.")
    if any(type(skills.get(key)) is not bool for key in SKILL_FIELDS):
        raise InputError("Each technical skill must be selected as true or false.")

    features = {
        "job_title": role,
        "country": country,
        "experience_level": EXPERIENCE_ALIASES[experience],
        "years_experience": float(years),
    }
    for key, column in SKILL_FIELDS.items():
        features[column] = int(skills[key])
    return features, {
        "jobRole": role,
        "country": country,
        "experienceLevel": EXPERIENCE_ALIASES[experience],
        "yearsExperience": float(years),
        "skills": {key: skills[key] for key in SKILL_FIELDS},
    }


def _mongo_error_response():
    current_app.logger.exception("MongoDB operation failed.")
    return jsonify(
        error="MongoDB is unavailable. Start MongoDB and try again; no history change was made."
    ), 503


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    app.config["JOB_DATA"] = load_dataset(Path(app.config["DATASET_PATH"]))

    @app.get("/")
    def home():
        return render_template("index.html", active_page="home")

    @app.get("/dashboard")
    def dashboard():
        return render_template("dashboard.html", active_page="dashboard")

    @app.get("/analysis")
    def analysis():
        return render_template("analysis.html", active_page="analysis")

    @app.get("/prediction")
    def prediction():
        analytics = build_analytics(current_app.config["JOB_DATA"])
        return render_template(
            "prediction.html",
            active_page="prediction",
            categories=analytics["categories"],
        )

    @app.get("/history")
    def history():
        return render_template("history.html", active_page="history")

    @app.get("/api/analytics")
    def analytics_api():
        return jsonify(build_analytics(current_app.config["JOB_DATA"]))

    @app.post("/api/predict")
    def predict_api():
        payload = request.get_json(silent=True)
        try:
            features, submitted = _validate_prediction(
                payload, current_app.config["JOB_DATA"]
            )
        except InputError as error:
            return jsonify(error=str(error)), 400

        try:
            model = get_model()
        except (FileNotFoundError, ValueError, OSError, ImportError, KeyError, AttributeError):
            current_app.logger.exception("The trained salary model is unavailable.")
            return jsonify(
                error="The trained salary model is unavailable or incompatible."
            ), 503

        input_frame = pd.DataFrame([features], columns=EXPECTED_FEATURES)
        try:
            predicted_salary = float(model.predict(input_frame)[0])
        except Exception:
            current_app.logger.exception("The trained model could not make a prediction.")
            return jsonify(error="The trained model could not generate a prediction."), 500
        if not math.isfinite(predicted_salary):
            current_app.logger.error("The trained model returned a non-finite salary.")
            return jsonify(error="The trained model returned an invalid estimate."), 500

        record = {
            "jobRole": submitted["jobRole"],
            "country": submitted["country"],
            "experienceLevel": submitted["experienceLevel"],
            "yearsExperience": submitted["yearsExperience"],
            "skills": submitted["skills"],
            "predictedSalary": round(predicted_salary, 2),
            "createdAt": datetime.now(timezone.utc),
        }
        try:
            get_predictions_collection().insert_one(record)
        except PyMongoError:
            return _mongo_error_response()
        return jsonify(
            prediction={
                "jobRole": record["jobRole"],
                "country": record["country"],
                "experienceLevel": record["experienceLevel"],
                "yearsExperience": record["yearsExperience"],
                "skills": record["skills"],
                "predictedSalary": record["predictedSalary"],
                "createdAt": record["createdAt"].isoformat(),
            },
            estimateNotice=(
                "This is an estimate from the existing model, not a guaranteed salary. "
                "The source dataset does not identify a currency."
            ),
        ), 201

    @app.get("/api/history")
    def history_api():
        search = request.args.get("search", "").strip()
        experience = request.args.get("experienceLevel", "").strip()
        query = {}
        if experience:
            allowed_levels = set(
                current_app.config["JOB_DATA"]["experience_level"].astype(str)
            ) | {"Executive"}
            if experience not in allowed_levels:
                return jsonify(error="Unknown experience-level filter."), 400
            query["experienceLevel"] = experience
        if search:
            pattern = re.escape(search[:100])
            search_clause = {
                "$or": [
                    {"jobRole": {"$regex": pattern, "$options": "i"}},
                    {"country": {"$regex": pattern, "$options": "i"}},
                ]
            }
            query = {"$and": [query, search_clause]} if query else search_clause

        try:
            cursor = (
                get_predictions_collection()
                .find(query)
                .sort("createdAt", DESCENDING)
                .limit(500)
            )
            records = [
                {
                    "id": str(record["_id"]),
                    "jobRole": record["jobRole"],
                    "country": record["country"],
                    "experienceLevel": record["experienceLevel"],
                    "yearsExperience": record["yearsExperience"],
                    "skills": record["skills"],
                    "predictedSalary": record["predictedSalary"],
                    "createdAt": record["createdAt"].isoformat(),
                }
                for record in cursor
            ]
        except PyMongoError:
            return _mongo_error_response()
        return jsonify(records=records, limit=500)

    @app.delete("/api/history/<record_id>")
    def delete_history_record(record_id):
        if not ObjectId.is_valid(record_id):
            return jsonify(error="Invalid prediction record ID."), 400
        try:
            result = get_predictions_collection().delete_one(
                {"_id": ObjectId(record_id)}
            )
        except PyMongoError:
            return _mongo_error_response()
        if result.deleted_count == 0:
            return jsonify(error="Prediction record was not found."), 404
        return jsonify(deleted=True)

    @app.delete("/api/history")
    def clear_history():
        try:
            result = get_predictions_collection().delete_many({})
        except PyMongoError:
            return _mongo_error_response()
        return jsonify(deleted=True, deletedCount=result.deleted_count)

    return app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=False)
