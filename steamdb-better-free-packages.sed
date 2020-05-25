#!/bin/sed -f
# First line makes it a function and runs it *now*
1d
# de-indent the 'let freePackages = '
0,/\t\+let/s/^\t\+//
# Define the function and set some variables after freePackages has been set
0,/^$/s//\0\nlet total_count = [ ...freePackages ].length;\nlet loaded_count = 0;\n\nsteamdb_function = function() {/
# Don't run the function immediately
$s/());$/;\n/

# Add to the loaded_count when removing pre-owned licenses
/\(\t\+\)\(freePackages.delete(.*)\);/s//\1if ( \2 ) {\n\1\tconsole.info("Already owned " + match[ 1 ]);\n\1\tloaded_count++\n\1}/

# Make a new variable for the truncated list
/^\t\+freePackages/,$s/freePackages/fiftyFreePackages/
s/fiftyFreePackages = /let \0/

# Add a sucess action when claiming licenses
/^\(\t\+\)\().always( requestNext );\)$/s//\1).done( function( data ) {\n\1\tconsole.info("Successfully claimed code " + fiftyFreePackages[ index ]);\n\1\tfreePackages.delete(fiftyFreePackages[ index ]);\n\1\tloaded_count++;\n\1}\2/

# Cleanup the progress display
/{loaded}/s/fiftyFreePackages.length/total_count/
/{loaded}/s/loaded/loaded_count/
/Reloading…/s|^\(\t\+\)'Reloading…',|\1'Waiting…',\n\1`Loaded <b>${loaded_count}</b>/${total_count}.`,|

# Print the time instead of reloading the page
s/location.reload()/console.info("Finished at "+Date())/

# Run the function now, and every hour
$a steamdb_function();
$a setInterval(steamdb_function, 1000*60*60);
