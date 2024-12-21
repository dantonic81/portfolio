document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('addToPortfolioModal');
    const nameInput = document.getElementById('cryptoName');
    const abbreviationInput = document.getElementById('cryptoAbbreviation');
    const amountInput = document.getElementById('cryptoAmount');
    const confirmAddButton = document.getElementById('confirmAdd');

    // Set up the modal with crypto details
    document.querySelectorAll('.add-to-portfolio').forEach(button => {
        button.addEventListener('click', function() {
            const name = this.getAttribute('data-name');
            const abbreviation = this.getAttribute('data-id');

            nameInput.value = name;
            abbreviationInput.value = abbreviation;
            amountInput.value = '';
        });
    });

    // Handle confirm button click
    confirmAddButton.addEventListener('click', function() {
        const name = nameInput.value;
        const abbreviation = abbreviationInput.value;
        const amount = parseFloat(amountInput.value);

        if (!amount || amount <= 0) {
            alert('Please enter a valid amount.');
            return;
        }

        // Send data to the server
        fetch('/portfolio/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, abbreviation, amount })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Crypto added to portfolio successfully!');
                // Close the modal
                $('#addToPortfolioModal').modal('hide');
                location.reload();
            } else {
                alert(`Error: ${data.error}`);
            }
        })
        .catch(error => console.error('Error:', error));
    });
});