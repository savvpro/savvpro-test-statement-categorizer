import pandas as pd
from io import BytesIO


def parse_csv(file_content: bytes):
    dataframe = pd.read_csv(BytesIO(file_content))

    required_columns = {
        "date",
        "description",
        "amount",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    return dataframe.to_dict(orient="records")