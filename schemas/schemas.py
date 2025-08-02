# Example schema for testing purposes

schema_image_200 = {
    "title": "Schema for Dog Image",
    "description": "Schema for validating dog image data from The Dog API",
    "type": "object",
    "properties": {
        "id": {
            "type": "string"
        },
        "url": {
            "type": "string"
        },
        "width": {
            "type": "number"
        },
        "height": {
            "type": "number"
        },
        "breeds": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "weight": {
                        "type": "object",
                        "properties": {
                            "imperial": {
                                "type": "string"
                            },
                            "metric": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "imperial",
                            "metric"
                        ]
                    },
                    "height": {
                        "type": "object",
                        "properties": {
                            "imperial": {
                                "type": "string"
                            },
                            "metric": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "imperial",
                            "metric"
                        ]
                    },
                    "id": {
                        "type": "number"
                    },
                    "name": {
                        "type": "string"
                    },
                    "bred_for": {
                        "type": "string"
                    },
                    "breed_group": {
                        "type": "string"
                    },
                    "life_span": {
                        "type": "string"
                    },
                    "temperament": {
                        "type": "string"
                    },
                    "reference_image_id": {
                        "type": "string"
                    }
                },
                "required": [
                    "weight",
                    "height",
                    "id",
                    "name",
                    "bred_for",
                    "breed_group",
                    "life_span",
                    "temperament",
                    "reference_image_id"
                ]
            }
        }
    },
    "required": [
        "id",
        "url",
        "width",
        "height",
        "breeds"
    ]
}
