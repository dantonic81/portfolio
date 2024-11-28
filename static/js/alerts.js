document.addEventListener("DOMContentLoaded", () => {
  const alertForm = document.getElementById('alertForm');
  const setAlertsButton = document.querySelector('[data-toggle="modal"][data-target="#setAlertsModal"]');
  const saveAlertsButton = document.getElementById('saveAlertsButton'); // Reference the Save Alerts button
  const searchInput = document.createElement('input'); // Create the search bar dynamically

  let ownedCoins = [];

  // Style the search input
  searchInput.id = 'searchCoin';
  searchInput.name = 'searchCoin';
  searchInput.type = 'text';
  searchInput.placeholder = 'Search for a coin...';
  searchInput.classList.add('form-control', 'mb-4'); // Add Bootstrap classes for styling

  // Insert the search input at the top of the form
  alertForm.before(searchInput);

  setAlertsButton.addEventListener('click', async () => {
    try {
      // Fetch the owned coins when the modal button is clicked
      ownedCoins = await fetchOwnedCoins();

      // Populate the modal with data
      populateAlertForm(ownedCoins);

      // Add event listener to search input to filter coins dynamically
      searchInput.addEventListener('input', () => filterCoins(searchInput.value, ownedCoins));
    } catch (error) {
      console.error("Error fetching owned coins:", error);
    }
  });

  async function fetchOwnedCoins() {
    const response = await fetch('/get-owned-coins');
    if (!response.ok) {
      throw new Error('Failed to fetch owned coins');
    }

    const ownedCoins = await response.json();
    console.log(ownedCoins); // Log the response to see its structure
    return ownedCoins; // Ensure this is the correct structure
  }

  function populateAlertForm(coins) {
    // Clear any existing content in the form
    alertForm.innerHTML = '';

    coins.forEach(coin => {
      const coinElement = document.createElement('div');
      coinElement.classList.add('form-group', 'mb-4', 'p-3', 'border', 'rounded', 'shadow-sm'); // Added styling classes

      // Use 'name' for the coin's name and 'abbreviation' for the coin's symbol
      coinElement.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3">
          <label for="alert-${coin.abbreviation}-more" class="h5">${coin.name}</label>
        </div>
        <div class="d-flex flex-column">
          <div class="form-check mb-2">
            <input class="form-check-input" type="radio" name="alert-${coin.abbreviation}" id="alert-${coin.abbreviation}-more" value="more">
            <label class="form-check-label" for="alert-${coin.abbreviation}-more">
              More than
            </label>
          </div>
          <div class="form-check mb-3">
            <input class="form-check-input" type="radio" name="alert-${coin.abbreviation}" id="alert-${coin.abbreviation}-less" value="less">
            <label class="form-check-label" for="alert-${coin.abbreviation}-less">
              Less than
            </label>
          </div>
          <div class="d-flex align-items-center">
            <input type="number" class="form-control" id="alert-value-${coin.abbreviation}" name="alert-value-${coin.abbreviation}" placeholder="Value in USD" aria-label="Value in USD">
            <span class="ml-2 text-muted">USD</span>
          </div>
        </div>
      `;

      alertForm.appendChild(coinElement); // Add each coin's alert options to the form
    });
  }

  function filterCoins(query, coins) {
    console.log("Filtering coins with query:", query); // Debug log
    const filteredCoins = coins.filter(coin =>
      coin.name.toLowerCase().includes(query.toLowerCase()) ||
      coin.abbreviation.toLowerCase().includes(query.toLowerCase())
    );

    console.log("Filtered coins:", filteredCoins); // Debug log
    populateAlertForm(filteredCoins); // Rebuild the form with the filtered coins
  }

  // Add functionality for saving alerts
  saveAlertsButton.addEventListener('click', async () => {
    const formData = new FormData(alertForm);
    const alerts = [];

    for (let [name, value] of formData.entries()) {
      if (name.startsWith('alert-') && value) {
        const coinAbbreviation = name.split('-')[1];
        const alertValue = formData.get(`alert-value-${coinAbbreviation}`);
        const coin = ownedCoins.find(c => c.abbreviation === coinAbbreviation);

        if (coin && alertValue) {
          alerts.push({
            name: coin.name,
            cryptocurrency: coinAbbreviation,
            alert_type: value,
            threshold: parseFloat(alertValue),
          });
        }
      }
    }

    try {
      for (const alert of alerts) {
        const response = await fetch('/api/set_alert', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(alert),
        });

        if (!response.ok) {
          throw new Error(`Failed to save alert: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('Alert saved successfully:', result);
      }

      alert('Alerts saved successfully!');
    } catch (error) {
      console.error('Error saving alerts:', error);
      alert('An error occurred while saving alerts.');
    }
  });
});
