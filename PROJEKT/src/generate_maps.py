import pandas as pd
import geopandas as gpd
import folium
from folium import plugins
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans
import os
import json

# Konfiguracja
DATA_PATH = 'processed_data/usa_quality_of_life_data.csv'
SHAPEFILE_PATH = 'tl_2025_us_county/tl_2025_us_county.shp'
OUTPUT_MAP_PATH = 'output_maps/map_usa_WOW_advanced.html'

# Upewnij się, że folder wyjściowy istnieje
os.makedirs('output_maps', exist_ok=True)

print("1. Loading Data...")
# Wczytanie CSV
df = pd.read_csv(DATA_PATH, dtype={'GEOID': str})
# Wczytanie Shapefile
gdf_raw = gpd.read_file(SHAPEFILE_PATH)

# Złączenie danych
print("Merging data...")
gdf = gdf_raw.merge(df, on='GEOID', how='inner')

# Fix column names if collision occurred (NAME in both files)
if 'NAME_x' in gdf.columns:
    gdf = gdf.rename(columns={'NAME_x': 'NAME'})
if 'NAME_y' in gdf.columns:
    gdf = gdf.drop(columns=['NAME_y'])

# Czyszczenie i Scoring
print("2. Calculating Scores and Clusters...")
gdf_clean = gdf.dropna(subset=['Median_Home_Price', 'Median_Income']).copy()
gdf_clean['Homicide_Rate_per_100k'] = gdf_clean['Homicide_Rate_per_100k'].fillna(0)
gdf_clean['Education_Bach_Plus_Pct'] = gdf_clean['Education_Bach_Plus_Pct'].fillna(gdf_clean['Education_Bach_Plus_Pct'].median())
gdf_clean['Poverty_Rate_Pct'] = gdf_clean['Poverty_Rate_Pct'].fillna(gdf_clean['Poverty_Rate_Pct'].median())
gdf_clean['Unemployment_Rate_Pct'] = gdf_clean['Unemployment_Rate_Pct'].fillna(gdf_clean['Unemployment_Rate_Pct'].median())

# Scoring
scaler = MinMaxScaler()
cols_positive = ['Median_Income', 'Education_Bach_Plus_Pct']
cols_negative = ['Home_Price_to_Income_Ratio', 'Poverty_Rate_Pct', 'Unemployment_Rate_Pct', 'Homicide_Rate_per_100k']

# Scale for Scoring Calculation (Negative inverted)
norm_df = pd.DataFrame(scaler.fit_transform(gdf_clean[cols_positive + cols_negative]), 
                       columns=cols_positive + cols_negative, 
                       index=gdf_clean.index)

for col in cols_negative:
    norm_df[col] = 1 - norm_df[col]

W_AFFORDABILITY = 0.35
W_SAFETY = 0.20
W_INCOME = 0.15
W_EDUCATION = 0.15
W_POVERTY = 0.15

gdf_clean['QoL_Score'] = (
    norm_df['Home_Price_to_Income_Ratio'] * W_AFFORDABILITY +
    norm_df['Homicide_Rate_per_100k'] * W_SAFETY +
    norm_df['Median_Income'] * W_INCOME +
    norm_df['Education_Bach_Plus_Pct'] * W_EDUCATION +
    norm_df['Poverty_Rate_Pct'] * W_POVERTY
) * 100

# === ML K-MEANS CLUSTERING ===
# Use pure scaled data (not inverted) for clustering
X = scaler.fit_transform(gdf_clean[['Median_Home_Price', 'Median_Income', 'Poverty_Rate_Pct', 
                                    'Homicide_Rate_per_100k', 'Education_Bach_Plus_Pct']])
kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
gdf_clean['Cluster'] = kmeans.fit_predict(X)
# Make clusters categorical strings for proper mapping
gdf_clean['Cluster_Label'] = "C" + gdf_clean['Cluster'].astype(str)

# Filtrowanie geometrii (uproszczenie)
print("3. Preparing Geometry...")
gdf_map = gdf_clean[~gdf_clean['STATEFP'].isin(['02', '15', '72'])].copy()
gdf_map['geometry'] = gdf_map.simplify(tolerance=0.05) 

# --- PRZYGOTOWANIE DANYCH TOP 10 ---
print("Preparing Top 10 Tables...")

def get_top10_html(df, col, name, ascending=False):
    # Sort
    top = df.sort_values(by=col, ascending=ascending).head(10)
    # Select cols
    top = top[['NAME', col]]
    # Rename for display
    top.columns = ['Hrabstwo', name]
    # To HTML
    return top.to_html(classes='table table-striped table-hover table-condensed table-responsive', index=False, border=0)

html_qol = get_top10_html(gdf_clean, 'QoL_Score', 'Wynik QoL')
html_safety = get_top10_html(gdf_clean, 'Homicide_Rate_per_100k', 'Zabójstwa/100k', ascending=True) # Im mniej tym lepiej
html_housing = get_top10_html(gdf_clean, 'Home_Price_to_Income_Ratio', 'Cena/Zarobki', ascending=True) # Im mniej tym lepiej

print("4. Generating Map...")
# 1. Tworzymy bazową mapę (Ciemny motyw wygląda nowocześnie)
m = folium.Map(location=[37.0902, -95.7129], zoom_start=4, tiles=None)
folium.TileLayer('CartoDB dark_matter', name="Dark Mode", control=True).add_to(m)
folium.TileLayer('OpenStreetMap', name="Light Mode", control=True).add_to(m)

# Styl dla dymków (tooltip)
style_tooltip = "background-color: black; color: white; font-family: arial; font-size: 12px; padding: 10px; border-radius: 5px;"

# --- WARSTWY ---

# Funkcja tworząca Choropleth + Tooltip
def create_choropleth(data, columns, fill_color, legend_name, tooltip_fields, tooltip_aliases, name, show=False, bins=6):
    c = folium.Choropleth(
        geo_data=data,
        name=name,
        data=data,
        columns=columns,
        key_on='feature.properties.GEOID',
        fill_color=fill_color,
        fill_opacity=0.8,
        line_opacity=0.3,
        line_weight=0.5,
        legend_name=legend_name,
        highlight=True,
        show=show, 
        bins=bins,
        overlay=True # Treat as overlay for LayerControl
    )
    
    # Tooltip to GeoJson
    folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
        style=style_tooltip
    ).add_to(c.geojson)
    
    return c

# Tworzenie warstw (obiektów Choropleth)
cp_qol = create_choropleth(gdf_map, ['GEOID', 'QoL_Score'], 'RdYlGn', 'QoL Score', 
                          ['NAME', 'QoL_Score'], ['Hrabstwo:', 'QoL:'], 
                          "🏆 Quality of Life", show=True)

cp_clusters = create_choropleth(gdf_map, ['GEOID', 'Cluster'], 'Set1', 'Cluster ID',
                               ['NAME', 'Cluster_Label'], ['Hrabstwo:', 'Profil:'], 
                               "🧩 ML Clusters", show=False, bins=5)

cp_safety = create_choropleth(gdf_map, ['GEOID', 'Homicide_Rate_per_100k'], 'OrRd', 'Homicide Rate',
                             ['NAME', 'Homicide_Rate_per_100k'], ['Hrabstwo:', 'Zabójstwa:'], 
                             "🛡️ Safety", show=False)

cp_housing = create_choropleth(gdf_map, ['GEOID', 'Home_Price_to_Income_Ratio'], 'Spectral_r', 'Price/Income Ratio',
                              ['NAME', 'Home_Price_to_Income_Ratio'], ['Hrabstwo:', 'Ratio:'], 
                              "🏠 Affordability", show=False)

# Add LAYERS to Map using add_child or add_to
# Note: Adding them to map makes them visible/exist in DOM.
m.add_child(cp_qol)
m.add_child(cp_clusters)
m.add_child(cp_safety)
m.add_child(cp_housing)

# --- PLAYER 2: RADIO BUTTONS (GroupedLayerControl) ---
# GroupedLayerControl with exclusive_groups creates Radio Buttons!
folium.plugins.GroupedLayerControl(
    groups={'Mapy Tematyczne (Wybierz jedną)': [cp_qol, cp_clusters, cp_safety, cp_housing]},
    exclusive_groups=True,
    collapsed=False
).add_to(m)


# --- PLAYER 3: DYNAMIC TABLE (Custom HTML/JS) ---
# Inject HTML for the floating panel
floating_panel_html = f"""
<div id="info-panel" style="
    position: fixed;
    bottom: 50px;
    left: 50px;
    width: 300px;
    height: auto;
    max-height: 400px;
    background-color: rgba(255, 255, 255, 0.9);
    border: 2px solid grey;
    border-radius: 10px;
    z-index: 9999;
    font-family: Arial, sans-serif;
    font-size: 12px;
    overflow-y: auto;
    box-shadow: 3px 3px 10px rgba(0,0,0,0.5);
    padding: 10px;
    display: block; /* Default visible */
">
    <h4 style="margin-top:0; text-align:center; border-bottom:1px solid #ccc; padding-bottom:5px;">
        📊 Top 10: <span id="layer-title">Quality of Life</span>
    </h4>
    
    <div id="table-qol" style="display:block;">
        {html_qol}
    </div>
    <div id="table-clusters" style="display:none;">
        <p style="text-align:center; padding:20px;"><i>Wybierz inny widok (Klastry to dane jakościowe)</i></p>
    </div>
    <div id="table-safety" style="display:none;">
        {html_safety}
    </div>
    <div id="table-housing" style="display:none;">
        {html_housing}
    </div>
    <div style="text-align:center; margin-top:10px; font-size:10px; color:#666;">
        Kliknij warstwę w legendzie, aby zmienić tabelę.
    </div>
</div>

<script>
    // Dictionary mapping Layer Name -> Div ID
    var layerMap = {{
        "🏆 Quality of Life": "table-qol",
        "🧩 ML Clusters": "table-clusters",
        "🛡️ Safety": "table-safety",
        "🏠 Affordability": "table-housing"
    }};

    // Function to update table
    function updateTable(layerName) {{
        console.log("Layer selected:", layerName);
        
        // Update Title
        var titleSpan = document.getElementById('layer-title');
        if (titleSpan) titleSpan.innerText = layerName.replace(/🏆|🧩|🛡️|🏠/g, '').trim();

        // Hide all
        for (var key in layerMap) {{
            var divId = layerMap[key];
            var el = document.getElementById(divId);
            if (el) el.style.display = 'none';
        }}

        // Show active
        if (layerName in layerMap) {{
            var activeId = layerMap[layerName];
            var activeEl = document.getElementById(activeId);
            if (activeEl) activeEl.style.display = 'block';
        }}
    }}
    
    window.onload = function() {{
        // Czekamy na załadowanie mapy
        // Szukamy obiektu mapy w window
        for(var name in window) {{
            if (name.startsWith('map_') && window[name] instanceof L.Map) {{
                var map = window[name];
                console.log("Map found via auto-discovery:", name);
                
                // Add listener for layer changes
                map.on('overlayadd', function(e) {{
                    updateTable(e.name);
                }});
                
                // Initial update
                updateTable("🏆 Quality of Life");
                break;
            }}
        }}
    }};
</script>
"""

# Add the floating panel to map root
m.get_root().html.add_child(folium.Element(floating_panel_html))


# --- DODATKI ---
# 1. WYSZUKIWARKA
plugins.Search(
    layer=cp_qol.geojson, # Important: Search needs GeoJson or LayerGroup, not Choropleth macro object
    geom_type='Polygon',
    placeholder='Szukaj hrabstwa...',
    collapsed=True,
    search_label='NAME',
    weight=3
).add_to(m)

# 2. MINI MAPA
plugins.MiniMap(toggle_display=True).add_to(m)

# Zapisujemy
print(f"Saving to {OUTPUT_MAP_PATH}...")
m.save(OUTPUT_MAP_PATH)
print("Done!")
