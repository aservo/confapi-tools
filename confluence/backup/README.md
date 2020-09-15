# Confluence Bulk Export / Import Scripts

## Installation
Install requirements:

```pip3 install -r requirements.txt```

make scripts executable:

```chmod +x export.py import.py```

## Help

For both export and import scripts there is a help function showing how to pass the parameters

```
./import.py -h
./export.py -h
```

## Sample Usage Export

export base-url spacekey1,spacekey2 --username my_username --password my_password

```=
./export.py http://localhost:1990/confluence KEY,ds --username admin --password admin
```

or

```=
python3 export.py http://localhost:1990/confluence KEY,ds --username admin --password admin
```

or prompt for password

```=
export.py http://localhost:1990/confluence KEY,ds
python3 export.py http://localhost:1990/confluence KEY,ds
```

## Sample Usage Import
import base-url unix-wildcard1 unix-wildcard2 --username my_username --password my_password
```=
./import.py http://localhost:1990/confluence Confluence.zip *.xml.zip --username admin --password admin
```

or

```=
python3 import.py http://localhost:1990/confluence Confluence.zip *.xml.zip --username admin --password admin
```

or prompt for password

```=
./import.py http://localhost:1990/confluence Confluence.zip *.xml.zip
python3 import.py http://localhost:1990/confluence Confluence.zip *.xml.zip
```