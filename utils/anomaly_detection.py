from sklearn.ensemble import IsolationForest
from typing import List, Dict, Any, Tuple


def preprocess_data(
    gainers: List[Dict[str, Any]], losers: List[Dict[str, Any]]
) -> Tuple[List[List[float]], List[str]]:
    """
    Extract features and coin IDs from gainers and losers.

    Args:
        gainers (List[Dict[str, Any]]): List of gainers.
        losers (List[Dict[str, Any]]): List of losers.

    Returns:
        Tuple[List[List[float]], List[str]]: Features for outlier detection and coin IDs.
    """
    features = []
    coin_ids = []

    for coin in gainers + losers:
        price = coin.get("current_price", 0.0)  # Default to 0.0 if not available
        market_cap = coin.get("market_cap", 0.0)
        total_volume = coin.get("total_volume", 0.0)

        features.append([price, market_cap, total_volume])
        coin_ids.append(coin.get("id", "unknown"))

    return features, coin_ids


def detect_outliers(
    features: List[List[float]], contamination: float = 0.1
) -> List[int]:
    """
    Use Isolation Forest to detect outliers.

    Args:
        features (List[List[float]]): Numerical features for the model.
        contamination (float): The proportion of outliers in the data.

    Returns:
        List[int]: Array of anomaly labels (-1 for outliers, 1 for inliers).
    """
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(features)
    return model.predict(features).tolist()


def make_hashable(coin: Any) -> Any:
    """
    Recursively convert dictionaries or lists to hashable tuples.

    Args:
        coin (Any): Data to be converted.

    Returns:
        Any: Hashable representation of the data.
    """
    if isinstance(coin, dict):
        return tuple((k, make_hashable(v)) for k, v in coin.items())
    elif isinstance(coin, list):
        return tuple(make_hashable(v) for v in coin)
    return coin  # Return primitive values unchanged


def format_coin(coin: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a coin dictionary to include key fields.

    Args:
        coin (Dict[str, Any]): Original coin data.

    Returns:
        Dict[str, Any]: Formatted coin dictionary.
    """
    return {
        "id": coin.get("id", "N/A"),
        "name": coin.get("name", "N/A"),
        "rank": coin.get("market_cap_rank", "N/A"),
        "current_price": coin.get("current_price", "N/A"),
        "percentage_gain": coin.get("price_change_percentage_24h", "N/A"),
        "market_cap": coin.get("market_cap", "N/A"),
        "volume": coin.get("total_volume", "N/A"),
        "image": coin.get("image", "N/A"),
    }


def combine_results(
    labels: List[int], gainers: List[Dict[str, Any]], losers: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Combine gainers and losers with their outlier labels.

    Args:
        labels (List[int]): Outlier labels (-1 for outliers, 1 for inliers).
        gainers (List[Dict[str, Any]]): List of gainers.
        losers (List[Dict[str, Any]]): List of losers.

    Returns:
        Dict[str, List[Dict[str, Any]]]: Dictionary with outliers and inliers.
    """
    combined = gainers + losers
    seen = set()
    unique_combined = []
    filtered_labels = []

    for i, coin in enumerate(combined):
        formatted_coin = format_coin(coin)
        coin_tuple = make_hashable(formatted_coin)

        if coin_tuple not in seen:
            seen.add(coin_tuple)
            unique_combined.append(formatted_coin)
            filtered_labels.append(labels[i])  # Keep corresponding label

    outliers = [
        unique_combined[i] for i, label in enumerate(filtered_labels) if label == -1
    ]
    inliers = [
        unique_combined[i] for i, label in enumerate(filtered_labels) if label == 1
    ]

    return {"outliers": outliers, "inliers": inliers}
