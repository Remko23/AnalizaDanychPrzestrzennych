import pandas as pd
from census import Census
from us import states
import os
import glob

from dotenv import load_dotenv

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
# Klucz API z pliku .env
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY')

# Rok danych Census ACS-5
CENSUS_YEAR = 2021 # 2022/2023 może być dostępny, 2021 jest bezpieczny dla pełnych danych 5-letnich

# Ścieżki do plików (uruchamianie z katalogu ADP)
ZILLOW_HOME_VALUE_PATH = 'County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv'
ZILLOW_RENT_PATH = 'County_zori_uc_sfrcondomfr_sm_month.csv'
# Plik CDC jest w formacie TSV mimo rozszerzenia .xls
HOMICIDE_PATH = 'Underlying Cause of Death, 2018-2023, Single Race.xls'
OUTPUT_FILE = 'processed_data/usa_quality_of_life_data.csv'

# ==========================================
# 1. CENSUS DATA FETCHING
# ==========================================
def get_census_data(api_key=None, year=2021):
    print("Pobieranie danych z Census API...")
    c = Census(api_key, year=year)
    
    # Kody zmiennych ACS-5
    # B19013_001E: Median Household Income
    # B15003_022E - B15003_025E: Bachelor's degree and higher
    # B15003_001E: Total pop 25+
    # B17001_002E: Income below poverty level
    # B17001_001E: Total pop for poverty status
    # B23025_005E: Unemployed
    # B23025_002E: In labor force
    
    fields = [
        'NAME',
        'B19013_001E', 
        'B15003_001E', 'B15003_022E', 'B15003_023E', 'B15003_024E', 'B15003_025E',
        'B17001_001E', 'B17001_002E',
        'B23025_002E', 'B23025_005E'
    ]
    
    try:
        # Pobierz dane dla wszystkich hrabstw (counties) we wszystkich stanach
        print("Pobieranie danych dla wszystkich stanów (może zająć chwilę)...")
        # Używamy Census.ALL ('*') dla stanu i hrabstwa, aby pobrać wszystko
        data_raw = c.acs5.state_county(fields, Census.ALL, Census.ALL)
    except Exception as e:
        print(f"Błąd pobierania wszystkich danych: {e}")
        print("Próba pobrania danych tylko dla Kalifornii (CA) jako test...")
        try:
            data_raw = c.acs5.state_county(fields, states.CA.fips, Census.ALL)
        except Exception as e2:
            print(f"Krytyczny błąd API Census: {e2}")
            print("Sprawdź klucz API. Jeśli go nie masz, zarejestruj się na http://api.census.gov/data/key_signup.html")
            return pd.DataFrame()

    df = pd.DataFrame(data_raw)
    
    # Tworzenie GEOID (State FIPS + County FIPS)
    df['GEOID'] = df['state'].astype(str).str.zfill(2) + df['county'].astype(str).str.zfill(3)
    
    # Obliczenia wskaźników
    # 1. Median Income
    df['Median_Income'] = df['B19013_001E'].astype(float)
    
    # 2. Education % (Bachelor's +)
    bach_plus = (
        df['B15003_022E'].astype(float) + 
        df['B15003_023E'].astype(float) + 
        df['B15003_024E'].astype(float) + 
        df['B15003_025E'].astype(float)
    )
    pop_25 = df['B15003_001E'].astype(float)
    df['Education_Bach_Plus_Pct'] = (bach_plus / pop_25) * 100
    
    # 3. Poverty Rate %
    poverty_pop = df['B17001_002E'].astype(float)
    total_pov_pop = df['B17001_001E'].astype(float)
    df['Poverty_Rate_Pct'] = (poverty_pop / total_pov_pop) * 100
    
    # 4. Unemployment Rate %
    unemployed = df['B23025_005E'].astype(float)
    labor_force = df['B23025_002E'].astype(float)
    df['Unemployment_Rate_Pct'] = (unemployed / labor_force) * 100
    
    # Selekcja kolumn
    final_cols = ['GEOID', 'NAME', 'Median_Income', 'Education_Bach_Plus_Pct', 'Poverty_Rate_Pct', 'Unemployment_Rate_Pct']
    return df[final_cols] 

# ==========================================
# 2. ZILLOW DATA PROCESSING
# ==========================================
def process_zillow_data(zhvi_path, zori_path):
    print("Przetwarzanie danych Zillow...")
    
    # --- Home Values (ZHVI) ---
    if os.path.exists(zhvi_path):
        df_zhvi = pd.read_csv(zhvi_path)
        # Tworzenie GEOID
        df_zhvi['GEOID'] = df_zhvi['StateCodeFIPS'].astype(str).str.zfill(2) + \
                           df_zhvi['MunicipalCodeFIPS'].astype(str).str.zfill(3)
        
        # Wybór ostatniej kolumny z datą (ceny)
        date_cols = [c for c in df_zhvi.columns if c[:2] == '20'] # kolumny zaczynające się od 20xx
        latest_date = date_cols[-1]
        print(f"Najnowsze dane o cenach domów z: {latest_date}")
        
        df_zhvi = df_zhvi[['GEOID', latest_date]].rename(columns={latest_date: 'Median_Home_Price'})
        # print(f"Przykładowe GEOIDs z Zillow (ZHVI): {df_zhvi['GEOID'].head().tolist()}")
    else:
        print(f"Brak pliku: {zhvi_path}")
        df_zhvi = pd.DataFrame(columns=['GEOID', 'Median_Home_Price'])

    # --- Rentals (ZORI) ---
    if os.path.exists(zori_path):
        df_zori = pd.read_csv(zori_path)
        # Tworzenie GEOID
        df_zori['GEOID'] = df_zori['StateCodeFIPS'].astype(str).str.zfill(2) + \
                           df_zori['MunicipalCodeFIPS'].astype(str).str.zfill(3)
        
        date_cols = [c for c in df_zori.columns if c[:2] == '20']
        latest_date = date_cols[-1]
        print(f"Najnowsze dane o czynszach z: {latest_date}")
        
        df_zori = df_zori[['GEOID', latest_date]].rename(columns={latest_date: 'Median_Rent'})
    else:
        print(f"Brak pliku: {zori_path}")
        df_zori = pd.DataFrame(columns=['GEOID', 'Median_Rent'])
        
    # Merge Zillow data
    df_zillow = pd.merge(df_zhvi, df_zori, on='GEOID', how='outer')
    return df_zillow

# ==========================================
# 3. HOMICIDE DATA PROCESSING (CDC)
# ==========================================
def process_homicide_data(filepath):
    print("Przetwarzanie danych o zabójstwach (CDC)...")
    if not os.path.exists(filepath):
        print(f"Brak pliku: {filepath}")
        return pd.DataFrame(columns=['GEOID', 'Homicide_Rate_per_100k'])
    
    try:
        # Plik CDC to TSV (rozdzielany tabulatorami)
        df = pd.read_csv(filepath, sep='\t', dtype={'County Code': str})
        
        # Filtrujemy wiersze z przypisami (Notes is NaN for valid data usually, but verify)
        # CDC adds footer notes, usually 'Notes' column is non-null for them
        # Valid data has County Code
        df = df[df['County Code'].notna()]
        
        # Konwersja
        df['Deaths'] = pd.to_numeric(df['Deaths'], errors='coerce').fillna(0)
        df['Population'] = pd.to_numeric(df['Population'], errors='coerce').fillna(0)
        
        # Agregacja 5-letnia (Suma zgonów / Suma populacji * 100k)
        # Sum_Pop to suma osobo-lat.
        
        df_agg = df.groupby('County Code')[['Deaths', 'Population']].sum().reset_index()
        df_agg['Homicide_Rate_per_100k'] = (df_agg['Deaths'] / df_agg['Population']) * 100000
        
        df_agg = df_agg.rename(columns={'County Code': 'GEOID'})
        df_agg['GEOID'] = df_agg['GEOID'].str.zfill(5)
        
        # print("Homicide preview:")
        # print(df_agg.head())
        
        return df_agg[['GEOID', 'Homicide_Rate_per_100k']]
        
    except Exception as e:
        print(f"Błąd przetwarzania pliku zabójstw: {e}")
        return pd.DataFrame(columns=['GEOID', 'Homicide_Rate_per_100k'])

# ==========================================
# 4. MAIN PIPELINE
# ==========================================
def main():
    # 1. Pobierz Census
    df_census = get_census_data(CENSUS_API_KEY, CENSUS_YEAR)
    if df_census.empty:
        print("Nie udało się pobrać danych Census. Przerywanie.")
        return

    # 2. Przetwórz Zillow
    df_zillow = process_zillow_data(ZILLOW_HOME_VALUE_PATH, ZILLOW_RENT_PATH)

    # 3. Przetwórz Zabójstwa
    df_homicide = process_homicide_data(HOMICIDE_PATH)
    
    # 4. Merge All
    print("Łączenie danych...")
    df_final = pd.merge(df_census, df_zillow, on='GEOID', how='left')
    df_final = pd.merge(df_final, df_homicide, on='GEOID', how='left')
    
    # 5. Obliczenia pochodne
    # Home Price to Income Ratio
    df_final['Home_Price_to_Income_Ratio'] = df_final['Median_Home_Price'] / df_final['Median_Income']
    
    # 6. Eksport
    print(f"Zapisywanie do {OUTPUT_FILE}...")
    df_final.to_csv(OUTPUT_FILE, index=False)
    print("Gotowe!")
    print(df_final.head())

if __name__ == "__main__":
    main()
