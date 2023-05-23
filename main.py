# Data cleansing d'un fichier fournisseur
#
# Nettoyer les données du fichier fournisseur « Test JUNGLE BIKE BBB.xls » afin d'en extraire les
# informations suivantes :
#
# - Type de produit
# - Dimensions (différents champs)
# - Taille
# - Contenance
# - Couleur
# - Modèle

import pandas as pd
import re
import numpy as np
from datetime import datetime

df = pd.read_excel('JUNGLE BIKE BBB.xlsx')
colors = pd.read_csv('Couleur.csv')
color_correction = pd.read_csv('color_map.csv')
colors = colors.to_numpy().reshape(colors.shape[0])

# Making first row as a header
df.columns = df.iloc[0]
# Dropping the first row
df.drop(df.index[0], inplace=True)
df.reset_index(drop=True, inplace=True)

# Adding more required columns
parameter_list = ['Type_de_produit', 'Longueur(mm)', 'Largeur(mm)', 'Hauteur(mm)', 'Rayon Ø(mm)', 'Volume(L)', 'Taille', 'Contenance',
    'Couleur', 'Modèle']
df[parameter_list] = np.nan

# Mapping for product
product_type = df.loc[
    (pd.isna(df['Désignation']) == False) & (pd.isna(df['Gamme'])) & (pd.isna(df['PRIX PUBLIC ttc*'])) & (
        pd.isna(df['TARIF BASE HT**'])) & (pd.isna(df['TARIF BASE HT**']))]
product_type = product_type.iloc[:, :2]
# Getting read of all spaces, coz it's a dictionary
product_type['Rèf.'] = product_type['Rèf.'].str.strip()
# Making upper case for all entries
product_type['Désignation'] = product_type['Désignation'].str.upper()

# DATA CORRECTION!!!!!
product_type['Rèf.'].replace('BBSQ', 'BBS', inplace=True)

for i in range(color_correction.shape[0]):
    df['Gamme'].replace(color_correction['color_EN'][i], color_correction['color_FR'][i], inplace=True)
    df['Désignation'].replace(color_correction['color_EN'][i], color_correction['color_FR'][i], inplace=True)

# Dropping index, coz we need to keep track of the index
product_type.reset_index(inplace=True)
df_product_drop = product_type

# Filling np.nan by previous valyue and making a dictionary with its index and its type
product_type = product_type.fillna(method='ffill').groupby('Rèf.').apply(
    lambda dfg: dfg.drop(['Rèf.'], axis=1).to_dict(orient='list'))
# I need index as a column in order to set a type
df.reset_index(inplace=True)

df['Désignation'] = df['Désignation'].str.lower()


# Mapping color
def color_func(x):
    temp = []
    if not pd.isna(x['Gamme']) and type(x['Gamme']) == str:
        for item in re.split(' |/', x['Gamme'].lower()):
            if item in colors:
                temp.append(item)
    if not pd.isna(x['Désignation']):
        for item in re.split(' |/', x['Désignation'].lower()):
            if item in colors:
                temp.append(item)

    x['Couleur'] = np.nan if len(temp) == 0 else '/'.join(temp)
    for item in temp:
        x['Désignation'] = x['Désignation'].replace(item, '')
    return x


def product_func(x):
    # we cannot look up for np.nan values in a dictionary, thus this check-point
    if not pd.isna(x['Rèf.']):
        # Splitting the reference prefix from number suffix in order to look up in a dictionary
        local_ref = x['Rèf.'].split('-')[0].strip()
        if local_ref in product_type.keys():
            # if len(product_type[local_ref]['Désignation']) == 1:
            #     return (product_type[local_ref]['Désignation'][0] if not pd.isna(x['Rèf.']) else np.nan)
            # else:
            i = 0
            while i < len(product_type[local_ref]['index']) - 1:
                if product_type[local_ref]['index'][i] <= x['index'] < product_type[local_ref]['index'][i + 1]:
                    break
                i += 1
            x['Type_de_produit'] = (product_type[local_ref]['Désignation'][i] if not pd.isna(x['Rèf.']) else np.nan)
            for item in re.split('\s|-', x['Type_de_produit'].lower()):
                regex = '(' + item + ')|(' + item[:-1] + ')'
                x['Désignation'] = re.sub(regex, '', x['Désignation'])
    return x


def size_func(x):
    temp = set()
    if not pd.isna(x['Désignation']):
        match = re.findall(r'\bS\b|\bM\b|\bL\b|\bXL\b|\bXXL\b|\bXXXL\b|\bENFANT\b|\bUNI-TAILLE\b|\bUNI TAILLE\b',
                           str(x['Désignation']).upper())
        if match:
            temp.update(match)
    if not pd.isna(x['Gamme']):
        match = re.findall(r'\bS\b|\bM\b|\bL\b|\bXL\b|\bXXL\b|\bXXXL\b|\bENFANT\b|\bUNI-TAILLE\b|\bUNI TAILLE\b',
                           str(x['Gamme']).upper())
        if match:
            temp.update(match)

    if 'UNI TAILLE' in temp:
        temp.remove('UNI TAILLE')
        temp.add('UNI-TAILLE')

    if len(temp) > 1:
        if 'UNI-TAILLE' in temp:
            temp.remove('UNI-TAILLE')
        if 'ENFANT' in temp:
            temp.remove('ENFANT')

    # for item in temp:
    #     x['Désignation'] =

    x['Taille'] = np.nan if len(temp) == 0 else '/'.join(temp)
    if not pd.isna(x['Taille']):
        for item in re.split('\s|-', x['Taille'].lower()):
            regex = '(' + item + ')|(' + item[:-1] + ')'
            x['Désignation'] = re.sub(regex, '', x['Désignation'])
    return x


def convertion_to_mm(number):
    if number.find('-') == -1:
        try:
            return eval(number.replace('cm', '*10').replace('m', '*1000').replace('mtr', '*1000').strip())
        except:
            return number
    else:
        return number


def rayon_func(x):
    rayon = None
    # getting Radius and length
    if not pd.isna(x['Gamme']):
        str_loc = str(x['Gamme']).lower()
        match = re.search('(\d+\s*(mm|cm)\s*ø)|(\d+\s*ø\s*(mm|cm))|(\d+\s*ø)|(ø\s*\d+\s*-\s*\d)|(ø\s*\d+\s*(mm|cm)?)',
                          str_loc)
        if match:
            match = match.regs[0]
            x['Rayon Ø(mm)'] = rayon = convertion_to_mm(re.sub('\s|ø|mm', '', str_loc[match[0]: match[1]]))
            # deleting from Désignation
            x['Gamme'] = re.sub(
                '(\d+\s*(mm|cm)\s*ø)|(\d+\s*ø\s*(mm|cm))|(\d+\s*ø)|(ø\s*\d+\s*-\s*\d)|(ø\s*\d+\s*(mm|cm)?)', '',
                x['Gamme'], flags=re.IGNORECASE)
            x['Désignation'] = re.sub(
                '(\d+\s*(mm|cm)\s*ø)|(\d+\s*ø\s*(mm|cm))|(\d+\s*ø)|(ø\s*\d+\s*-\s*\d)|(ø\s*\d+\s*(mm|cm)?)', '',
                x['Désignation'], flags=re.IGNORECASE)

    if rayon == None and not pd.isna(x['Désignation']):
        str_loc = str(x['Désignation']).lower()
        match = re.search('(\d+\s*(mm|cm)\s*ø)|(\d+\s*ø\s*(mm|cm))|(\d+\s*ø)|(ø\s*\d+\s*-\s*\d)|(ø\s*\d+\s*(mm|cm)?)',
                          str_loc)
        if match:
            match = match.regs[0]
            x['Rayon Ø(mm)'] = convertion_to_mm(re.sub('\s|ø|mm', '', str_loc[match[0]: match[1]]))
            # deleting from Désignation
            x['Désignation'] = re.sub(
                '(\d+\s*(mm|cm)\s*ø)|(\d+\s*ø\s*(mm|cm))|(\d+\s*ø)|(ø\s*\d+\s*-\s*\d)|(ø\s*\d+\s*(mm|cm)?)', '',
                x['Désignation'], flags=re.IGNORECASE)

    return x


def LWH_func(x):
    Length = None
    Width = None
    Height = None

    # three digits
    str_loc = str(x['Gamme']).lower()
    match = re.search(
        '(\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?)|'
        '(\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?)', str_loc)
    if match:
        match = match.regs[0]
        str_loc = str_loc[match[0]: match[1]].split('x')

        Length = str_loc[0].replace(',', '.').replace('mm', '')
        Width = str_loc[1].replace(',', '.').replace('mm', '')
        Height = str_loc[2].replace(',', '.').replace('mm', '')

        Length = convertion_to_mm(Length)
        Width = convertion_to_mm(Width)
        Height = convertion_to_mm(Height)
        x['Désignation'] = re.sub(
            '(\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?)|'
            '(\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?)', '', x['Désignation'])
        x['Longueur(mm)'] = Length
        x['Largeur(mm)'] = Width
        x['Hauteur(mm)'] = Height
        return x
    if not pd.isna(x['Désignation']):
        str_loc = str(x['Désignation']).lower()
        match = re.search(
            '(\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?)|'
            '(\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?)', str_loc)
        if match:
            match = match.regs[0]
            str_loc = str_loc[match[0]: match[1]].split('x')

            Length = str_loc[0].replace(',', '.').replace('mm', '')
            Width = str_loc[1].replace(',', '.').replace('mm', '')
            Height = str_loc[2].replace(',', '.').replace('mm', '')

            Length = convertion_to_mm(Length)
            Width = convertion_to_mm(Width)
            Height = convertion_to_mm(Height)
            x['Désignation'] = re.sub(
                '(\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?)|'
                '(\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?)', '', x['Désignation'])
            x['Longueur(mm)'] = Length
            x['Largeur(mm)'] = Width
            x['Hauteur(mm)'] = Height
            return x

        # two digits
        if not pd.isna(x['Gamme']):
            str_loc = str(x['Gamme']).lower()

            match = re.search('(\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?)|'
                              '(\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?)', str_loc)
            if match:
                match = match.regs[0]
                str_loc = str_loc[match[0]: match[1]].split('x')

                Length = str_loc[1].replace(',', '.').replace('mm', '')
                Width = str_loc[0].replace(',', '.').replace('mm', '')

                Length = convertion_to_mm(Length)
                Width = convertion_to_mm(Width)
                Height = np.nan
                # deleting information frm the field
                x['Désignation'] = re.sub('(\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?)|'
                                          '(\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?)', '', x['Désignation'])
                x['Longueur(mm)'] = Length
                x['Largeur(mm)'] = Width
                x['Hauteur(mm)'] = Height
                return x

        if not pd.isna(x['Désignation']):
            str_loc = str(x['Désignation']).lower()
            match = re.search('(\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?)|'
                              '(\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?)', str_loc)
            if match:
                match = match.regs[0]
                str_loc = str_loc[match[0]: match[1]].split('x')

                Length = str_loc[1].replace(',', '.').replace('mm', '')
                Width = str_loc[0].replace(',', '.').replace('mm', '')

                Length = convertion_to_mm(Length)
                Width = convertion_to_mm(Width)
                Height = np.nan

                x['Désignation'] = re.sub('(\d+(\.|\,)?\d+\s*(mm|cm|m)?\s*x\s*\d+(\.|\,)?\d+\s*(mm|cm|m)?)|'
                                          '(\d+\s*(mm|cm|m)?\s*x\s*\d+\s*(mm|cm|m)?)', '', x['Désignation'])

                x['Longueur(mm)'] = Length
                x['Largeur(mm)'] = Width
                x['Hauteur(mm)'] = Height
                return x

    # TODO: one digit
    if not pd.isna(x['Gamme']):
        str_loc = str(x['Gamme']).lower()

        match = re.search('(\d+(\.|\,)?\d+\s*(mm|cm|m))|(\d+\s*(mm|cm|m))', str_loc)
        if match:
            match = match.regs[0]
            str_loc = str_loc[match[0]: match[1]].split('x')

            Length = str_loc[0].replace(',', '.').replace('mm', '')
            Length = convertion_to_mm(Length)
            Width = np.nan
            Height = np.nan
            # deleting information frm the field
            x['Désignation'] = re.sub('(\d+(\.|\,)?\d+\s*(mm|cm|m))|(\d+\s*(mm|cm|m))', '', x['Désignation'])
            x['Longueur(mm)'] = Length
            x['Largeur(mm)'] = Width
            x['Hauteur(mm)'] = Height
            return x

    if not pd.isna(x['Désignation']):
        str_loc = str(x['Désignation']).lower()
        match = re.search('(\d+(\.|\,)?\d+\s*(mm|cm|m))|(\d+\s*(mm|cm|m))', str_loc)
        if match:
            match = match.regs[0]
            str_loc = str_loc[match[0]: match[1]].split('x')

            Length = str_loc[0].replace(',', '.').replace('mm', '')
            Length = convertion_to_mm(Length)
            Width = np.nan
            Height = np.nan

            x['Désignation'] = re.sub('(\d+(\.|\,)?\d+\s*(mm|cm|m)?)|(\d+\s*(mm|cm|m)?)', '', x['Désignation'])

            x['Longueur(mm)'] = Length
            x['Largeur(mm)'] = Width
            x['Hauteur(mm)'] = Height
            return x

    x['Longueur(mm)'] = Length
    x['Largeur(mm)'] = Width
    x['Hauteur(mm)'] = Height
    return x


def volume_func(x):
    if not pd.isna(x['Gamme']):
        str_loc = str(x['Gamme']).lower()
        match = re.search('(\d+(\.|\,)?\d+l)|(\d+l)', str_loc)
        if match:
            match = match.regs[0]
            str_loc = str_loc[match[0]: match[1]]
            x['Volume(L)'] = str_loc.replace(',', '.').replace('l', '')
            x['Désignation'] = re.sub('(\d+(\.|\,)?\d+l)|(\d+l)', '', x['Désignation'])
            return x
    if not pd.isna(x['Désignation']):
        str_loc = str(x['Désignation']).lower()
        match = re.search('(\d+(\.|\,)?\d+l)|(\d+l)', str_loc)
        if match:
            match = match.regs[0]
            str_loc = str_loc[match[0]: match[1]]
            x['Volume(L)'] = str_loc.replace(',', '.').replace('l', '')
            x['Désignation'] = re.sub('(\d+(\.|\,)?\d+l)|(\d+l)', '', x['Désignation'])
            return x
    return x


# 892	BSB-19	Sacoche tube horizontal TopTank X 1,5L
def capacity_func(x):
    if not pd.isna(x['Gamme']):
        str_loc = str(x['Gamme']).lower()
        match = re.search('(\d+\s*pcs)|(^\d+$)|((de)\s*\d+)', str_loc)
        if match:
            match = match.regs[0]
            str_loc = str_loc[match[0]: match[1]]
            x['Contenance'] = str_loc.replace('pcs', '').replace('de', '')
            x['Désignation'] = re.sub('(\(?\d+\s*pcs\)?)|((de)\s*\d+)', '', x['Désignation'])
            return x
    if not pd.isna(x['Désignation']):
        str_loc = str(x['Désignation']).lower()
        match = re.search('(\d+\s*pcs)|(^\d+$)|((de)\s*\d+)', str_loc)
        if match:
            match = match.regs[0]
            str_loc = str_loc[match[0]: match[1]]
            x['Contenance'] = str_loc.replace('pcs', '').replace('de', '')
            x['Désignation'] = re.sub('(\(?\d+\s*pcs\)?)|((de)\s*\d+)', '', x['Désignation'])
            return x
    return x


def type_func(x):

    if not pd.isna(x['Désignation']):
        x['Désignation'] = x['Désignation'].strip().replace('-', '')
        x['Modèle'] = re.sub('^de|^a|^à|(de\s*de)|(de\s*en)|de$|en$|\($', '', x['Désignation']).strip()
    return x


df = df.apply(product_func, axis=1)
df = df.apply(color_func, axis=1)
df = df.apply(size_func, axis=1)
# TODO: add do discs
df = df.apply(rayon_func, axis=1)
df = df.apply(LWH_func, axis=1)
df = df.apply(volume_func, axis=1)
df = df.apply(capacity_func, axis=1)
df = df.apply(type_func, axis=1)

# deleting titles string
# TODO: delete empty strings (left after converting from excel)
df = df.drop(df_product_drop['index'])
df_product_drop = df.loc[(pd.isna(df['Désignation'])) & (pd.isna(df['Gamme'])) & (pd.isna(df['PRIX PUBLIC ttc*'])) & (
    pd.isna(df['TARIF BASE HT**'])) & (pd.isna(df['TARIF BASE HT**']))]
df = df.drop(df_product_drop.index)

df.to_csv(f'tests/test_{datetime.now()}.csv')
df[['Rèf.'] + parameter_list].to_csv('JUNGLE_BIKE_BBB_CLEANED.csv')
