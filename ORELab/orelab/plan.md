I want to feed the data from excel into ORE engine. However, ORE seems to rely on xml. Then I need an engine to convert the excel files to xml files. Those xml files should be stored in a temporary folder. Then we can feed them into ORE engine. After the calculation is done, the temporary folder can be removed. In ORELab, write an engine to do the task

Requirements:
Format: Multiple sheets by trade type (cleaner, easier to maintain)
Trade Types: Interest Rate Swaps (fixed vs floating), FX Forwards, FX Options, Cross-Currency Swaps
Config: Portfolio + Netting only, reuse existing Static/ files
Temp Folder: Use db/temp_<timestamp>/ with auto-cleanup option
Output & Results: Copy results from Output/ to a specific location
API: Context manager (Option C) - Pythonic and safe
Validation: Moderate - catch obvious errors, let ORE handle complex ones
Error Handling: Skip invalid trades with warnings
Documentation: Provide sample Excel files with example trades
Location: ./ORELab/orelab/ package

Notes:
We need to be careful with the files' path. There are 3 main groups:
- main ore.xml file in db/
- trade data and netting data will come from excel and be converted to xml files in temporary folder
- static data files in db/Static

The important thing is every path will be relative to "inputPath" defined in ore.xml

