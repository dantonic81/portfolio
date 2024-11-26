document.addEventListener("DOMContentLoaded", () => {
  const alertForm = document.getElementById('alertForm');
  const setAlertsButton = document.querySelector('[data-toggle="modal"][data-target="#setAlertsModal"]');
  const searchInput = document.createElement('input');  // Create the search bar dynamically

  // Style the search input
  searchInput.type = 'text';
  searchInput.placeholder = 'Search for a coin...';
  searchInput.classList.add('form-control', 'mb-4');  // Add Bootstrap classes for styling

  // Insert the search input at the top of the form
  alertForm.before(searchInput);

  setAlertsButton.addEventListener('click', async () => {
    try {
      // Fetch the owned coins when the modal button is clicked
      const ownedCoins = await fetchOwnedCoins();

      // Populate the modal with data
      populateAlertForm(ownedCoins);
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
    console.log(ownedCoins);  // Log the response to see its structure
    return ownedCoins;  // Ensure this is the correct structure
  }

function populateAlertForm(ownedCoins) {
  // Clear any existing content in the form
  alertForm.innerHTML = '';

  ownedCoins.forEach(coin => {
    const coinElement = document.createElement('div');
    coinElement.classList.add('form-group', 'mb-4', 'p-3', 'border', 'rounded', 'shadow-sm');  // Added styling classes

    // Use 'name' for the coin's name and 'abbreviation' for the coin's symbol
    coinElement.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-3">
        <label for="alert-${coin.abbreviation}-more" class="h5">${coin.name}</label>
      </div>
      <div class="d-flex flex-column">
        <div class="form-check mb-2">
          <!-- Ensure unique id and name for each radio button -->
          <input class="form-check-input" type="radio" name="alert-${coin.abbreviation}" id="alert-${coin.abbreviation}-more" value="more">
          <label class="form-check-label" for="alert-${coin.abbreviation}-more">
            More than
          </label>
        </div>
        <div class="form-check mb-3">
          <!-- Ensure unique id and name for each radio button -->
          <input class="form-check-input" type="radio" name="alert-${coin.abbreviation}" id="alert-${coin.abbreviation}-less" value="less">
          <label class="form-check-label" for="alert-${coin.abbreviation}-less">
            Less than
          </label>
        </div>
        <div class="d-flex align-items-center">
          <!-- Ensure a unique id and name for the number input -->
          <input type="number" class="form-control" id="alert-value-${coin.abbreviation}" name="alert-value-${coin.abbreviation}" placeholder="Value in USD" aria-label="Value in USD">
          <span class="ml-2 text-muted">USD</span>
        </div>
      </div>
    `;

    alertForm.appendChild(coinElement);  // Add each coin's alert options to the form
  });

  // Add event listener to search input to filter coins dynamically
  searchInput.addEventListener('input', () => filterCoins(searchInput.value, ownedCoins));
}


  function filterCoins(query, coins) {
    // Filter the coins based on the search query
    const filteredCoins = coins.filter(coin =>
      coin.name.toLowerCase().includes(query.toLowerCase()) ||
      coin.abbreviation.toLowerCase().includes(query.toLowerCase())
    );

    // Repopulate the form with the filtered list
    alertForm.innerHTML = '';  // Clear the existing content
    populateAlertForm(filteredCoins);  // Rebuild the form with the filtered coins
  }
});
