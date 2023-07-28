from math import floor
import pandas as pd
import gspread


class GoogleSheetPipeline:
    spreadsheet_name = "Bali Properties 1"

    def __init__(self):
        self.sh = self.connect_to_spreasheet()

    def connect_to_spreasheet(self):
        gc = gspread.service_account(filename="creds.json")
        sh = gc.open(self.spreadsheet_name).sheet1
        return sh

    def keep_float(self, value):
        if type(value) == str:
            value = eval(value)
        if value is not None:
            dec = value - floor(value)
            if dec > 0:
                return round(value, 1)
            else:
                return int(value)
        else:
            return ""

    def get_columns(self, col_index):
        return self.sh.col_values(col_index)

    def to_list(self, obj):
        secure_number = [
            "bedrooms",
            "bathrooms",
            "land_size",
            "build_size",
            "price",
            "years",
        ]
        for key in secure_number:
            try:
                value = self.keep_float(obj[key])
            except:
                value = ""
            obj[key] = value

        return [
            obj.get("source", ""),
            obj.get("id", ""),
            obj.get("scrape_date", ""),
            obj.get("list_date", ""),
            obj.get("title", ""),
            obj.get("location", ""),
            obj.get("leasehold_freehold", ""),
            obj.get("years", ""),
            obj.get("bedrooms", ""),
            obj.get("bathrooms", ""),
            obj.get("land_size", ""),
            obj.get("build_size", ""),
            obj.get("price", ""),
            obj.get("property_link", ""),
            obj.get("image", ""),
            obj.get("availbility", ""),
            obj.get("description", ""),
        ]

    def append_to_spreadsheet(self, items):
        data = list(map(self.to_list, items))
        try:
            self.sh.append_rows(data)
            return True
        except Exception as err:
            print(err)
            # print(data)
            return False


if __name__ == "__main__":
    # type the filename you want to append
    filename = "kibarer.csv"

    # assign the pipeline and get the already uploaded url
    sh = GoogleSheetPipeline()
    blacklist = sh.get_columns(14)

    # read csv
    df = pd.read_csv(filename)

    # collect the not uploaded property
    items = []
    for row in df.iterrows():
        item = row.fillna("").to_dict()
        if item["property_link"] in blacklist:
            continue
        items.append(item)

    # upload the items as rows
    uploaded = sh.append_to_spreadsheet(items)
