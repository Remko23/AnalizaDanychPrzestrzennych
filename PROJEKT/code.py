import pandas as pd
import geopandas as gpd
import folium
from folium import plugins
from us import states
import os
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

CENSUS_DATA_PATH = 'data/census_data.csv'
ZILLOW_HOME_VALUE_PATH = 'data/zillow_home_price.csv'
ZILLOW_RENT_PATH = 'data/zillow_rent.csv'
HOMICIDE_PATH = 'data/cdc_homicide.xls'
SCHOOL_PATH = 'data/schools.csv'
SHAPEFILE_PATH = 'data/tl_2025_us_county/tl_2025_us_county.shp'


# ----------

def get_census_data(filepath):      
    df = pd.read_csv(filepath, dtype={'GEOID': str})
    return df


def process_zillow_data(zhvi_path, zori_path):
    df_zhvi = pd.read_csv(zhvi_path)
    df_zhvi['GEOID'] = df_zhvi['StateCodeFIPS'].astype(str).str.zfill(2) + df_zhvi['MunicipalCodeFIPS'].astype(str).str.zfill(3)
    date_cols = [c for c in df_zhvi.columns if c[:3] == '202']
    latest_date = date_cols[-1]
    df_zhvi = df_zhvi[['GEOID', latest_date]].rename(columns={latest_date: 'Median_Home_Price'})

    df_zori = pd.read_csv(zori_path)
    df_zori['GEOID'] = df_zori['StateCodeFIPS'].astype(str).str.zfill(2) + df_zori['MunicipalCodeFIPS'].astype(str).str.zfill(3)
    date_cols = [c for c in df_zori.columns if c[:3] == '202']
    latest_date = date_cols[-1]
    df_zori = df_zori[['GEOID', latest_date]].rename(columns={latest_date: 'Median_Rent'})
        
    return pd.merge(df_zhvi, df_zori, on='GEOID', how='outer')


def process_homicide_data(filepath):
    df = pd.read_csv(filepath, sep='\t', dtype={'County Code': str})
    df = df[df['County Code'].notna()]
    df['Deaths'] = pd.to_numeric(df['Deaths'], errors='coerce').fillna(0)
    df['Population'] = pd.to_numeric(df['Population'], errors='coerce').fillna(0)
    
    df_agg = df.groupby('County Code')[['Deaths', 'Population']].sum().reset_index()
    df_agg['Homicide_Rate_per_100k'] = (df_agg['Deaths'] / df_agg['Population']) * 100000
    
    df_agg = df_agg.rename(columns={'County Code': 'GEOID'})
    df_agg['GEOID'] = df_agg['GEOID'].str.zfill(5)
    return df_agg[['GEOID', 'Homicide_Rate_per_100k', 'Deaths', 'Population']]


def process_school_data(filepath):    
    df = pd.read_csv(filepath, usecols=['CNTY'])
    df['GEOID'] = df['CNTY'].astype(str).str.zfill(5)
    return df.groupby('GEOID').size().reset_index(name='School_Count')



# ----------

# Load Data
df_census = get_census_data(CENSUS_DATA_PATH)
df_zillow = process_zillow_data(ZILLOW_HOME_VALUE_PATH, ZILLOW_RENT_PATH)
df_homicide = process_homicide_data(HOMICIDE_PATH).rename(columns={'Population': 'Population_CDC'})
df_schools = process_school_data(SCHOOL_PATH)

# Merge
df_final = pd.merge(df_census, df_zillow, on='GEOID', how='left')
df_final = pd.merge(df_final, df_homicide, on='GEOID', how='left')
df_final = pd.merge(df_final, df_schools, on='GEOID', how='left')

# Imputation 
df_final['STATEFP'] = df_final['GEOID'].str[:2]

state_stats = df_final.groupby('STATEFP')[['Deaths', 'Population_CDC']].sum().reset_index()
state_stats['State_Homicide_Rate'] = (state_stats['Deaths'] / state_stats['Population_CDC']) * 100000

df_final = pd.merge(df_final, state_stats[['STATEFP', 'State_Homicide_Rate']], on='STATEFP', how='left')

national_median = df_final['Homicide_Rate_per_100k'].median()
df_final['Homicide_Rate_imputed'] = df_final['Homicide_Rate_per_100k'].fillna(df_final['State_Homicide_Rate'])
df_final['Homicide_Rate_imputed'] = df_final['Homicide_Rate_imputed'].fillna(national_median)

df_final['Homicide_Rate_per_100k'] = df_final['Homicide_Rate_imputed']
df_final = df_final.drop(columns=['Deaths', 'Population_CDC', 'State_Homicide_Rate', 'Homicide_Rate_imputed', 'STATEFP'])

df_final['Home_Price_to_Income_Ratio'] = df_final['Median_Home_Price'] / df_final['Median_Income']

df_final['School_Count'] = df_final['School_Count'].fillna(0)
df_final['School_Density'] = (df_final['School_Count'] / df_final['Population']) * 1000
df_final['School_Density'] = df_final['School_Density'].replace([float('inf'), -float('inf')], 0).fillna(0)

# mapowanie
df_map_input = df_final.copy()


# ----------

os.makedirs('output_maps', exist_ok=True)

gdf_raw = gpd.read_file(SHAPEFILE_PATH)

gdf = gdf_raw.merge(df_map_input, on='GEOID', how='inner')
if 'NAME_x' in gdf.columns:
    gdf = gdf.rename(columns={'NAME_x': 'NAME'})
if 'NAME_y' in gdf.columns:
    gdf = gdf.drop(columns=['NAME_y'])

gdf_clean = gdf.dropna(subset=['Median_Home_Price', 'Median_Income']).copy()
gdf_clean['Homicide_Rate_per_100k'] = gdf_clean['Homicide_Rate_per_100k'].fillna(gdf_clean['Homicide_Rate_per_100k'].median())
gdf_clean['Education_Bach_Plus_Pct'] = gdf_clean['Education_Bach_Plus_Pct'].fillna(gdf_clean['Education_Bach_Plus_Pct'].median())
gdf_clean['Poverty_Rate_Pct'] = gdf_clean['Poverty_Rate_Pct'].fillna(gdf_clean['Poverty_Rate_Pct'].median())
gdf_clean['Unemployment_Rate_Pct'] = gdf_clean['Unemployment_Rate_Pct'].fillna(gdf_clean['Unemployment_Rate_Pct'].median())



# ----------

scaler = MinMaxScaler()
cols_positive = ['Median_Income', 'Education_Bach_Plus_Pct', 'School_Density']
cols_negative = ['Home_Price_to_Income_Ratio', 'Poverty_Rate_Pct', 'Unemployment_Rate_Pct', 'Homicide_Rate_per_100k']

norm_df = pd.DataFrame(scaler.fit_transform(gdf_clean[cols_positive + cols_negative]), 
                       columns=cols_positive + cols_negative, 
                       index=gdf_clean.index)

for col in cols_negative:
    norm_df[col] = 1 - norm_df[col]

W_AFFORDABILITY = 0.25
W_SAFETY = 0.20
W_INCOME = 0.15
W_EDUCATION = 0.15
W_POVERTY = 0.15
W_SCHOOLS = 0.10

gdf_clean['QoL_Score'] = (
    norm_df['Home_Price_to_Income_Ratio'] * W_AFFORDABILITY +
    norm_df['Homicide_Rate_per_100k'] * W_SAFETY +
    norm_df['Median_Income'] * W_INCOME +
    norm_df['Education_Bach_Plus_Pct'] * W_EDUCATION +
    norm_df['Poverty_Rate_Pct'] * W_POVERTY +
    norm_df['School_Density'] * W_SCHOOLS
) * 100

cols_to_round = ['QoL_Score', 'Homicide_Rate_per_100k', 'Home_Price_to_Income_Ratio', 
                 'Education_Bach_Plus_Pct', 'Poverty_Rate_Pct', 'Unemployment_Rate_Pct', 
                 'School_Density', 'Median_Income', 'Median_Home_Price', 'Median_Rent']

for col in cols_to_round:
    if col in gdf_clean.columns:
        gdf_clean[col] = gdf_clean[col].round(2)



# ----------
gdf_map = gdf_clean[~gdf_clean['STATEFP'].isin(['02', '15', '72'])].copy() 
gdf_map['geometry'] = gdf_map.simplify(tolerance=0.05) 


# ----------


def get_top10_html(df, col, name, ascending=False):
    top = df.sort_values(by=col, ascending=ascending).head(10)
    top = top[['NAME', col]]
    top.columns = ['Hrabstwo', name]
    return top.to_html(classes='table table-striped table-hover table-condensed table-responsive', index=False, border=0)

style_tooltip = "background-color: black; color: white; font-family: arial; font-size: 12px; padding: 10px; border-radius: 5px;"

def create_choropleth(data, columns, fill_color, legend_name, tooltip_fields, tooltip_aliases, name, show=False, bins=6):
    c = folium.Choropleth(
        geo_data=data, name=name, data=data, columns=columns,
        key_on='feature.properties.GEOID', fill_color=fill_color,
        fill_opacity=0.8, line_opacity=0.3, line_weight=0.5,
        legend_name=legend_name, highlight=True, show=show, bins=bins, overlay=True
    )
    folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, style=style_tooltip).add_to(c.geojson)
    return c


# ----------


html_qol = get_top10_html(gdf_clean, 'QoL_Score', 'Wynik QoL')
html_safety = get_top10_html(gdf_clean, 'Homicide_Rate_per_100k', 'Zabójstwa/100k', ascending=True)
html_housing = get_top10_html(gdf_clean, 'Home_Price_to_Income_Ratio', 'Cena/Zarobki', ascending=True)
html_income = get_top10_html(gdf_clean, 'Median_Income', 'Mediana Zarobków', ascending=False)
html_education = get_top10_html(gdf_clean, 'Education_Bach_Plus_Pct', 'Wyższe Wykształcenie %', ascending=False)
html_poverty = get_top10_html(gdf_clean, 'Poverty_Rate_Pct', 'Ubóstwo %', ascending=True)
html_unemployment = get_top10_html(gdf_clean, 'Unemployment_Rate_Pct', 'Bezrobocie %', ascending=True)
html_schools = get_top10_html(gdf_clean, 'School_Density', 'Szkoły/1k mieszk.', ascending=False)

m = folium.Map(location=[37.0902, -95.7129], zoom_start=4, tiles=None, zoom_control=True)
folium.TileLayer('CartoDB dark_matter', name="Dark Mode", control=True).add_to(m)
folium.TileLayer('OpenStreetMap', name="Light Mode", control=True).add_to(m)

cp_qol = create_choropleth(gdf_map, ['GEOID', 'QoL_Score'], 'RdYlGn', 'Wynik Jakości Życia (0-100)', 
                          ['NAME', 'QoL_Score'], ['Hrabstwo:', 'QoL:'], "Jakość Życia", show=True)
cp_safety = create_choropleth(gdf_map, ['GEOID', 'Homicide_Rate_per_100k'], 'OrRd', 'Zabójstwa na 100k',
                             ['NAME', 'Homicide_Rate_per_100k'], ['Hrabstwo:', 'Zabójstwa:'], "Bezpieczeństwo", show=False)
cp_housing = create_choropleth(gdf_map, ['GEOID', 'Home_Price_to_Income_Ratio'], 'Spectral_r', 'Stosunek Ceny Domu do Zarobków',
                              ['NAME', 'Home_Price_to_Income_Ratio'], ['Hrabstwo:', 'Ratio:'], "Przystępność Cenowa", show=False)
cp_income = create_choropleth(gdf_map, ['GEOID', 'Median_Income'], 'Greens', 'Mediana Zarobków ($)',
                              ['NAME', 'Median_Income'], ['Hrabstwo:', 'Zarobki:'], "Zarobki", show=False)
cp_education = create_choropleth(gdf_map, ['GEOID', 'Education_Bach_Plus_Pct'], 'Blues', 'Wyższe Wykształcenie (%)',
                                 ['NAME', 'Education_Bach_Plus_Pct'], ['Hrabstwo:', 'Wykształcenie:'], "Edukacja", show=False)
cp_poverty = create_choropleth(gdf_map, ['GEOID', 'Poverty_Rate_Pct'], 'Reds', 'Wskaźnik Ubóstwa (%)',
                               ['NAME', 'Poverty_Rate_Pct'], ['Hrabstwo:', 'Ubóstwo:'], "Ubóstwo", show=False)
cp_unemployment = create_choropleth(gdf_map, ['GEOID', 'Unemployment_Rate_Pct'], 'Purples', 'Stopa Bezrobocia (%)',
                                    ['NAME', 'Unemployment_Rate_Pct'], ['Hrabstwo:', 'Bezrobocie:'], "Bezrobocie", show=False)
cp_schools = create_choropleth(gdf_map, ['GEOID', 'School_Density'], 'YlOrBr', 'Szkoły na 1000 mieszk.',
                               ['NAME', 'School_Density'], ['Hrabstwo:', 'Szkoły/1k:'], "Dostępność Szkół", show=False)

m.add_child(cp_qol)
m.add_child(cp_safety)
m.add_child(cp_housing)
m.add_child(cp_income)
m.add_child(cp_education)
m.add_child(cp_poverty)
m.add_child(cp_unemployment)
m.add_child(cp_schools)

folium.plugins.GroupedLayerControl(
    groups={
        'Wybierz Wskaźnik': [cp_qol, cp_income, cp_housing, cp_poverty, cp_unemployment, cp_education, cp_safety, cp_schools]
    },
    exclusive_groups=True,
    collapsed=True
).add_to(m)

plugins.Search(layer=cp_qol.geojson, geom_type='Polygon', placeholder='Szukaj hrabstwa', collapsed=True, search_label='NAME', weight=3, position='topright').add_to(m)

floating_panel_html = f'''
<div id="info-panel" style="
    position: fixed; bottom: 50px; left: 50px; width: 300px; height: auto; max-height: 400px;
    background-color: rgba(255, 255, 255, 0.9); border: 2px solid grey; border-radius: 10px;
    z-index: 9999; font-family: Arial, sans-serif; font-size: 12px; overflow-y: auto;
    box-shadow: 3px 3px 10px rgba(0,0,0,0.5); padding: 10px; display: block;
">
    <h4 style="margin-top:0; text-align:center; border-bottom:1px solid #ccc; padding-bottom:5px;">
        Top 10: <span id="layer-title">Quality of Life</span>
    </h4>
    <div id="table-qol" style="display:block;">{html_qol}</div>
    <div id="table-safety" style="display:none;">{html_safety}</div>
    <div id="table-housing" style="display:none;">{html_housing}</div>
    <div id="table-income" style="display:none;">{html_income}</div>
    <div id="table-education" style="display:none;">{html_education}</div>
    <div id="table-poverty" style="display:none;">{html_poverty}</div>
    <div id="table-unemployment" style="display:none;">{html_unemployment}</div>
    <div id="table-schools" style="display:none;">{html_schools}</div>
    <div style="text-align:center; margin-top:10px; font-size:10px; color:#666;">
        Kliknij warstwę w legendzie, aby zmienić tabelę.
    </div>
</div>


<script>
    var layerMap = {{
        "Jakość Życia": "table-qol",
        "Bezpieczeństwo": "table-safety",
        "Przystępność Cenowa": "table-housing",
        "Zarobki": "table-income",
        "Edukacja": "table-education",
        "Ubóstwo": "table-poverty",
        "Bezrobocie": "table-unemployment",
        "Dostępność Szkół": "table-schools"
    }};


    function updateTable(layerName) {{
        console.log("Layer selected:", layerName);
        var titleSpan = document.getElementById('layer-title');
        if (titleSpan) titleSpan.innerText = layerName.trim();
        for (var key in layerMap) {{
            var divId = layerMap[key];
            var el = document.getElementById(divId);
            if (el) el.style.display = 'none';
        }}
        if (layerName in layerMap) {{
            var activeId = layerMap[layerName];
            var activeEl = document.getElementById(activeId);
            if (activeEl) activeEl.style.display = 'block';
        }}
    }}
    
    window.onload = function() {{
        for(var name in window) {{
            if (name.startsWith('map_') && window[name] instanceof L.Map) {{
                var map = window[name];
                map.on('overlayadd', function(e) {{ updateTable(e.name); }});
                updateTable("Jakość Życia");
                break;
            }}
        }}
    }};
</script>
'''

m.get_root().html.add_child(folium.Element(floating_panel_html))

# Wymuszenie pozycji wyszukiwarki za pomocą CSS (hack na uparte biblioteki)
css_hack = """
<style>
.leaflet-control-search {
    position: fixed !important;
    top: 70px !important;
    right: 10px !important;
    left: auto !important;
    bottom: auto !important;
    z-index: 10000;
}
</style>
"""
m.get_root().html.add_child(folium.Element(css_hack))

plugins.MiniMap(toggle_display=True).add_to(m)

m.save('output_maps/final_map_usa.html')


# ----------
gdf_static = gdf_map.copy()
gdf_static['QoL_Category'] = 'Pozostałe'

top10_idx = gdf_static.nlargest(10, 'QoL_Score').index
bottom10_idx = gdf_static.nsmallest(10, 'QoL_Score').index

gdf_static.loc[top10_idx, 'QoL_Category'] = 'Top 10 QoL'
gdf_static.loc[bottom10_idx, 'QoL_Category'] = 'Bottom 10 QoL'

color_map = {
    'Top 10 QoL': '#2ca25f',
    'Bottom 10 QoL': '#de2d26',
    'Pozostałe': '#bdbdbd'
}

fig, ax = plt.subplots(figsize=(16, 10))

gdf_static.plot(
    color=gdf_static['QoL_Category'].map(color_map),
    linewidth=0.2,
    edgecolor='white',
    ax=ax
)

import matplotlib.patches as mpatches

legend_elements = [
    mpatches.Patch(color='#2ca25f', label='10 najlepszych'),
    mpatches.Patch(color='#de2d26', label='10 najgorszych'),
    mpatches.Patch(color='#bdbdbd', label='Pozostałe hrabstwa')
]

ax.legend(
    handles=legend_elements,
    loc='upper right',
    frameon=True,
    title='Kategorie QoL'
)
ax.set_title(
    '10 najlepszych i najgorszych Hrabstw w USA',
    fontsize=18
)
ax.axis('off')

ax.set_xlim(-130, -60)
ax.set_ylim(23, 50)

def add_styled_table(ax, data, col_labels, loc, bbox, header_color, row_colors):
    table = ax.table(
        cellText=data.values,
        colLabels=col_labels,
        loc=loc,
        bbox=bbox,
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.2) # Scale height

    # Style cells
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor(header_color)
            cell.set_linewidth(0)
        else:
            cell.set_facecolor(row_colors[row % len(row_colors)])
            cell.set_linewidth(0)
            cell.set_text_props(color='black')
    return table

# Add labels to map
import matplotlib.patheffects as pe
from adjustText import adjust_text

texts = []

def LabelCounties(df_indices, rank_list, color, ax, texts_list):
    for idx, rank in zip(df_indices, rank_list):
        # Get geometry
        geom = gdf_static.loc[idx, 'geometry']
        # Find representative point (centroid)
        repr_point = geom.representative_point()
        x, y = repr_point.x, repr_point.y
        
        # Add text (initially at the centroid)
        t = ax.text(x, y, str(rank), fontsize=10, ha='center', va='center', 
                    color=color, weight='bold',
                    path_effects=[pe.withStroke(linewidth=2, foreground='black')])
        texts_list.append(t)

top10_data = gdf_static.loc[top10_idx, ['NAME', 'QoL_Score']].sort_values('QoL_Score', ascending=False)
top10_data.insert(0, 'Nr', range(1, 11))

LabelCounties(top10_data.index, top10_data['Nr'], '#2ca25f', ax, texts)

add_styled_table(
    ax, 
    top10_data, 
    ['Nr', 'Hrabstwo', 'Jakość Życia'], 
    'lower right', 
    [0.75, 0.05, 0.20, 0.25], 
    '#2ca25f', 
    ['#e5f5e0', '#ffffff']
)

bottom10_data = gdf_static.loc[bottom10_idx, ['NAME', 'QoL_Score']].sort_values('QoL_Score', ascending=True)
bottom10_data.insert(0, 'Nr', range(1, 11))

LabelCounties(bottom10_data.index, bottom10_data['Nr'], '#de2d26', ax, texts)

add_styled_table(
    ax, 
    bottom10_data, 
    ['Nr', 'Hrabstwo', 'Jakość Życia'], 
    'lower left', 
    [0.05, 0.05, 0.20, 0.25], 
    '#de2d26', # Header Red
    ['#fee0d2', '#ffffff'] # Alternating Light Red/White
)

adjust_text(texts, arrowprops=dict(arrowstyle='-|>', color='black', lw=1.5))

plt.tight_layout()
plt.savefig('output_maps/best_worst_map.png', dpi=300, bbox_inches='tight')
plt.show()
