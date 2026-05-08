-- 1. ENABLE EXTENSIONS
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 2. CREATE SCHEMAS
CREATE TABLE vessels (
    id SERIAL PRIMARY KEY,
    imo_number VARCHAR(10) UNIQUE NOT NULL,
    vessel_name VARCHAR(100) NOT NULL,
    vessel_type VARCHAR(50),
    year_built INT
);

CREATE TABLE compartments (
    id SERIAL PRIMARY KEY,
    vessel_id INT REFERENCES vessels(id),
    compartment_name VARCHAR(100),
    fluid_type VARCHAR(50),
    volume_m3 DECIMAL(10, 2),
    center_of_gravity_z DECIMAL(10, 2)
);

CREATE TABLE telemetry_logs (
    id SERIAL PRIMARY KEY,
    vessel_id INT REFERENCES vessels(id),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6),
    speed_knots DECIMAL(5, 2),
    fuel_consumption_lph DECIMAL(6, 2),
    wave_height_m DECIMAL(4, 2)
);

-- 3. INSERT VESSEL SEED DATA
INSERT INTO vessels (imo_number, vessel_name, vessel_type, year_built) VALUES
('IMO9123456', 'NAPA Voyager', 'Cruise Ship', 2018),
('IMO9988776', 'Nordic Tanker', 'Oil Tanker', 2021),
('IMO9112233', 'Baltic Carrier', 'Bulk Carrier', 2015),
('IMO9445566', 'Atlantic RoRo', 'RoRo', 2019),
('IMO9776655', 'Pacific Container', 'Container Ship', 2020);

-- 4. INSERT COMPARTMENT SEED DATA
INSERT INTO compartments (vessel_id, compartment_name, fluid_type, volume_m3, center_of_gravity_z) VALUES
(1, 'Ballast Tank 1P', 'Seawater', 450.50, -2.5),
(1, 'Ballast Tank 1S', 'Seawater', 450.50, -2.5),
(2, 'Cargo Hold 1', 'Crude Oil', 12500.00, 5.0),
(3, 'Heavy Fuel Oil Tank', 'HFO', 800.00, -4.0);

-- 5. GENERATE 50,000 ROWS OF TELEMETRY DATA
-- We use a CROSS JOIN with generate_series to quickly simulate 30 days of fleet data
INSERT INTO telemetry_logs (vessel_id, timestamp, latitude, longitude, speed_knots, fuel_consumption_lph, wave_height_m)
SELECT 
    v.id,
    NOW() - (random() * interval '30 days'),
    (random() * 180) - 90,     -- Random Latitude
    (random() * 360) - 180,    -- Random Longitude
    (random() * 15 + 5),       -- Random Speed between 5 and 20 knots
    (random() * 500 + 100),    -- Random Fuel Consumption
    (random() * 5)             -- Random Wave Height
FROM vessels v
CROSS JOIN generate_series(1, 10000);

-- 6. CREATE INDEXES (Good database practice)
CREATE INDEX idx_telemetry_vessel_id ON telemetry_logs(vessel_id);
CREATE INDEX idx_telemetry_timestamp ON telemetry_logs(timestamp);