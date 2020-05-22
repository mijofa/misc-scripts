let freePackages = new Set( [
[gamelist goes here]
	] );

let total_count = [ ...freePackages ].length;
let loaded_count = 0;

steamdb_function = function() {
	if( !location.href.startsWith( 'https://store.steampowered.com/account/licenses' ) ) {
		alert( 'Please run this on Steam\'s account licenses page.' );
		return;
	}

	[ ...document.querySelectorAll( 'a[href^="javascript:RemoveFreeLicense"]' ) ].forEach( ( element ) => {
		const match = element.href.match( /javascript:RemoveFreeLicense\( ([0-9]+), '/ );
		
		if( match !== null ) {
			if ( freePackages.delete( parseInt( match[ 1 ], 10 ) ) ) {
				console.debug("Already owned " + match[ 1 ]);
				loaded_count++
			}
		}
	} );

	let fiftyFreePackages = [ ...freePackages ].slice( -50 );

	let loaded = 0;
	let modal;

	const fetch = ( index ) => {
		window.jQuery.post(
			'https://store.steampowered.com/checkout/addfreelicense/' + fiftyFreePackages[ index ],
			{
				ajax: true,
				sessionid: window.g_sessionID,
			}
		).done( function( data ) {
			console.debug("Successfully claimed code " + fiftyFreePackages[ index ]);
			freePackages.delete(fiftyFreePackages[ index ]);
			loaded_count++;
		}).always( requestNext );
	};

	const requestNext = () => {
		if( modal ) {
			modal.Dismiss();
		}

		if( loaded < fiftyFreePackages.length ) {
			modal = window.ShowBlockingWaitDialog(
				'Executing…',
				`Loaded <b>${loaded_count}</b>/${total_count}.`
			);

			fetch( loaded++ );

			return;
		}

		window.ShowBlockingWaitDialog(
			'Waiting…',
			`Loaded <b>${loaded_count}</b>/${total_count}.`,
			'Keep in mind only 50 packages can be activated per hour.'
		);

		if( typeof GDynamicStore !== 'undefined' ) {
			GDynamicStore.InvalidateCache();
		}

	};

	requestNext();
};

steamdb_function();
setInterval(steamdb_function, 1000*60*60);
