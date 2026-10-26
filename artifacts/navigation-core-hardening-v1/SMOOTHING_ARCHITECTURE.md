# Smoothing architecture

`rawLocation` is the received GPS fix. `matchedLocation` is Location Engine output. `displayLocation` is marker-only interpolation (0.65). `cameraTarget` is look-ahead framing, smoothed separately into `cameraPosition` and `cameraBearing`.

Camera duration is adaptive after the measurement: 0–20 km/h 300 ms; 20–60 200 ms; 60–100 120 ms; >100 75 ms. Prediction limits and Location Engine recovery are unchanged.
