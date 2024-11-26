document.addEventListener("DOMContentLoaded", () => {
  const alertForm = document.getElementById('alertForm');
  const setAlertsButton = document.querySelector('[data-toggle="modal"][data-target="#setAlertsModal"]');

  setAlertsButton.addEventListener('click', async () => {
    try {
      // Fetch the owned coins when the modal button is clicked
      const ownedCoins = await fetchOwnedCoins();  // Assume this function fetches owned crypto data

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
          <input type="number" class="form-control" id="alert-value-${coin.abbreviation}" placeholder="Value in USD" aria-label="Value in USD">
          <span class="ml-2 text-muted">USD</span>
        </div>
      </div>
    `;

    alertForm.appendChild(coinElement);  // Add each coin's alert options to the form
  });
}
});
