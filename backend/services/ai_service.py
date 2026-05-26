import asyncio
import logging
import random
from uuid import UUID

from sqlalchemy.orm import Session

from models.meal_log import MealLog

logger = logging.getLogger(__name__)

MOCK_NUTRITION_DATA = {
    "breakfast": [
        {"calories": 380, "protein_g": 22, "carbs_g": 45, "fat_g": 12, "food_description": "Oatmeal with banana, eggs and almonds"},
        {"calories": 420, "protein_g": 28, "carbs_g": 38, "fat_g": 15, "food_description": "Greek yogurt parfait with granola and berries"},
        {"calories": 350, "protein_g": 18, "carbs_g": 42, "fat_g": 11, "food_description": "Whole wheat toast with avocado and poached eggs"},
    ],
    "lunch": [
        {"calories": 650, "protein_g": 38, "carbs_g": 72, "fat_g": 18, "food_description": "Grilled chicken rice bowl with roasted vegetables"},
        {"calories": 580, "protein_g": 32, "carbs_g": 65, "fat_g": 16, "food_description": "Quinoa salad with chickpeas, cucumber and feta"},
        {"calories": 720, "protein_g": 42, "carbs_g": 68, "fat_g": 22, "food_description": "Dal makhani with brown rice and cucumber raita"},
    ],
    "dinner": [
        {"calories": 720, "protein_g": 45, "carbs_g": 68, "fat_g": 22, "food_description": "Baked salmon with quinoa and roasted broccoli"},
        {"calories": 680, "protein_g": 40, "carbs_g": 62, "fat_g": 20, "food_description": "Chicken tikka with roti and mixed vegetable curry"},
        {"calories": 550, "protein_g": 35, "carbs_g": 58, "fat_g": 15, "food_description": "Grilled fish with sweet potato and steamed beans"},
    ],
    "snack": [
        {"calories": 180, "protein_g": 8,  "carbs_g": 24, "fat_g": 6,  "food_description": "Greek yogurt with mixed berries"},
        {"calories": 220, "protein_g": 12, "carbs_g": 18, "fat_g": 10, "food_description": "Boiled eggs with mixed nuts"},
        {"calories": 150, "protein_g": 6,  "carbs_g": 20, "fat_g": 5,  "food_description": "Apple slices with peanut butter"},
    ],
}


async def extract_nutrition_from_image(meal_log_id: UUID, meal_type: str, db: Session) -> None:
    """
    Mock AI nutrition extraction — simulates Gemini Vision API call.

    Production implementation:
      1. Read image bytes from Cloud Storage using signed URL
      2. Encode to base64
      3. POST to Gemini 1.5 Flash:
           https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent
         Body: { contents: [{ parts: [{ inline_data: {mime_type, data} }, { text: prompt }] }] }
         Prompt: "Analyze this meal image. Return JSON only:
                  {calories: int, protein_g: float, carbs_g: float, fat_g: float,
                   food_description: string}"
      4. Parse JSON response, validate schema
      5. Update meal_log with extracted values
    """
    try:
        # Mark as processing
        meal_log = db.query(MealLog).filter(MealLog.id == meal_log_id).first()
        if not meal_log:
            logger.warning(f"MealLog {meal_log_id} not found for AI extraction")
            return

        meal_log.extraction_status = "processing"
        db.commit()

        # Simulate AI processing delay (2s mock)
        await asyncio.sleep(2)

        # Pick random mock result for the meal type
        options = MOCK_NUTRITION_DATA.get(meal_type, MOCK_NUTRITION_DATA["lunch"])
        extracted = random.choice(options)

        # Re-fetch after await (db session may have changed)
        meal_log = db.query(MealLog).filter(MealLog.id == meal_log_id).first()
        if not meal_log:
            return

        meal_log.calories = extracted["calories"]
        meal_log.protein_g = extracted["protein_g"]
        meal_log.carbs_g = extracted["carbs_g"]
        meal_log.fat_g = extracted["fat_g"]
        meal_log.food_description = extracted["food_description"]
        meal_log.extraction_status = "completed"
        db.commit()

        logger.info(f"AI extraction completed for meal_log {meal_log_id}: {extracted['food_description']}")

    except Exception as e:
        logger.error(f"AI extraction failed for meal_log {meal_log_id}: {e}")
        try:
            meal_log = db.query(MealLog).filter(MealLog.id == meal_log_id).first()
            if meal_log:
                meal_log.extraction_status = "failed"
                meal_log.extraction_error = str(e)
                db.commit()
        except Exception as inner:
            logger.error(f"Failed to update error status: {inner}")
