from sklearn.ensemble import IsolationForest


def preprocess_data(gainers, losers):
    features = []
    coin_ids = []

    for coin in gainers + losers:
        # Access 'current_price' directly instead of 'usd'
        price = coin.get('current_price', 0)  # Default to 0 if not available

        features.append([
            price,
            coin.get("market_cap", 0),
            coin.get("total_volume", 0)
        ])

        coin_ids.append(coin.get("id", "unknown"))

    return features, coin_ids


def detect_outliers(features, contamination=0.1):
    """
    Use Isolation Forest to detect outliers.

    Args:
        features (numpy.ndarray): Numerical features for the model.
        contamination (float): The proportion of outliers in the data.

    Returns:
        numpy.ndarray: Array of anomaly labels (-1 for outliers, 1 for inliers).
    """
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(features)
    labels = model.predict(features)
    return labels


def make_hashable(coin):
    """Recursively convert dictionaries to hashable tuples."""
    if isinstance(coin, dict):
        return tuple((k, make_hashable(v)) for k, v in coin.items())  # Recursively convert dicts
    elif isinstance(coin, list):
        return tuple(make_hashable(v) for v in coin)  # Recursively convert lists
    else:
        return coin  # Return primitive values as they are (e.g., strings, numbers)


def combine_results(labels, gainers, losers):
    combined = gainers + losers

    # Remove duplicates by converting dictionaries to hashable tuples
    seen = set()
    unique_combined = []
    filtered_labels = []  # A list to store the filtered labels corresponding to unique_combined

    for i, coin in enumerate(combined):
        # Extracting and formatting key fields for caching
        formatted_coin = {
            'id': coin.get('id', 'N/A'),
            'name': coin.get('name', 'N/A'),
            'rank': coin.get('market_cap_rank', 'N/A'),
            'current_price': coin.get('current_price', 'N/A'),
            'percentage_gain': coin.get('price_change_percentage_24h', 'N/A'),
            'market_cap': coin.get('market_cap', 'N/A'),
            'volume': coin.get('total_volume', 'N/A'),
            'image': coin.get('image', 'N/A')
        }

        coin_tuple = make_hashable(formatted_coin)  # Convert the formatted coin dictionary to a hashable tuple

        if coin_tuple not in seen:
            seen.add(coin_tuple)
            unique_combined.append(formatted_coin)
            filtered_labels.append(labels[i])  # Keep the corresponding label

    # Now combine again with labels
    outliers = [unique_combined[i] for i, label in enumerate(filtered_labels) if label == -1]
    inliers = [unique_combined[i] for i, label in enumerate(filtered_labels) if label == 1]

    return {"outliers": outliers, "inliers": inliers}