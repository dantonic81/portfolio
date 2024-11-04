CREATE TABLE IF NOT EXISTS sample_data (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),
    value INTEGER
);

INSERT INTO sample_data (name, value)
VALUES ('Sample A', 100), ('Sample B', 200), ('Sample C', 300);