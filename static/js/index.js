$(document).ready(function() {
    // Add Asset Modal Form Submission
    $('#addAssetForm').submit(function(event) {
        event.preventDefault();  // Prevent the form from submitting normally

        // Log to verify that the event is triggered
        console.log("Form submitted");

        // Send the form data via AJAX or handle it as needed
        var formData = {
            name: $('#asset-name').val().trim().toLowerCase(),
            abbreviation: $('#asset-abbreviation').val().trim().toLowerCase(),
            amount: parseFloat($('#asset-amount').val())
        };

        console.log("Form data:", formData);

        $.ajax({
            url: '/add_asset',  // Adjust to your correct route
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function(response) {
                console.log("Asset saved:", response);

                // Close the Add Asset modal after success
                $('#addAssetModal').modal('hide');  // Make sure this targets the correct modal

                // Show success message
                alert('Asset added successfully!');
                location.reload();

            },
            error: function(xhr) {
                console.error("Error saving asset:", xhr);

                // Check for specific error messages
                if (xhr.status === 400 && xhr.responseJSON && xhr.responseJSON.error) {
                    // Display specific error message to the user
                    alert(xhr.responseJSON.error); // e.g., "Asset already exists!"
                } else {
                    // Fallback for other errors
                    alert('An unexpected error occurred. Please try again later.');
                }
            }
        });
    });

    // Clear the Add Asset form fields when the modal is closed
    $('#addAssetModal').on('hidden.bs.modal', function () {
        // Clear all input fields
        $('#addAssetForm')[0].reset();

        // Optionally clear custom validation messages or feedback
        $('#addAssetForm .is-invalid').removeClass('is-invalid');
        $('#addAssetForm .is-valid').removeClass('is-valid');
    });

    // Function to show the success message
    function showSuccessMessage(message) {
        var successMessage = $('<div>')
            .addClass('alert alert-success')
            .text(message)
            .appendTo('body')
            .fadeIn(500)
            .delay(2000)  // Display for 2 seconds
            .fadeOut(500, function() {
                $(this).remove();  // Remove the success message after fading out
            });
    }

    // Handle the search functionality for existing assets
    $('#searchAsset').on('input', function() {
        var query = $(this).val();  // Get the search term

        if (query.length >= 2) {  // Start searching after 2 characters
            $.ajax({
                url: '/search_assets',  // Adjust to your server route
                type: 'GET',
                data: { query: query },
                success: function(response) {
                    // Clear the previous results
                    $('#assetResults').empty();

                    // Check if results were found
                    if (response.assets.length > 0) {
                        response.assets.forEach(function(asset) {
                            // Add a list item for each matching asset
                            $('#assetResults').append(
                                `<li class="list-group-item" data-asset-id="${asset.id}" data-asset-name="${asset.asset_name}" data-asset-amount="${asset.amount}">
                                    ${asset.asset_name}
                                </li>`
                            );
                        });
                    } else {
                        $('#assetResults').append('<li class="list-group-item">No assets found</li>');
                    }
                },
                error: function(xhr, status, error) {
                    console.error("Error fetching assets:", error);
                }
            });
        } else {
            // Clear results if input is less than 2 characters
            $('#assetResults').empty();
        }
    });

    // Handle selecting an asset from the search results to edit or delete it
    $('#assetResults').on('click', 'li', function() {
        var assetId = $(this).data('asset-id');
        var assetName = $(this).data('asset-name');
        var assetAmount = $(this).data('asset-amount');

        // Populate the modal with the selected asset's data
        $('#edit-asset-id').val(assetId);
        $('#edit-asset-name').val(assetName);

        // Store the current amount in a data attribute
        $('#edit-asset-amount').data('current-amount', assetAmount);

        // Set the amount field to show the old amount as a placeholder
        $('#edit-asset-amount').attr('placeholder', 'Current Amount: ' + assetAmount);

        // Show the Edit Asset modal
        $('#editAssetModal').modal('show');

        // Close the dropdown by removing the "show" class or hiding the dropdown
        $('#assetResults').empty();  // Optionally clear the results after selection
    });

    // Handle saving changes to the asset
    $('#saveChangesButton').click(function() {
        var assetId = $('#edit-asset-id').val();
        var name = $('#edit-asset-name').val();
        var amount = $('#edit-asset-amount').val();

        var formData = { id: assetId, name: name, amount: amount };

        $.ajax({
            url: '/update_asset',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function(response) {
                alert('Asset updated successfully!');
                $('#editAssetModal').modal('hide');
                location.reload();  // Optionally reload to update the page
            },
            error: function(xhr, status, error) {
                alert('Error updating asset.');
                console.error("Error updating asset:", error);
            }
        });
    });

    // Handle deleting the asset
    $('#deleteAssetButton').click(function() {
        var assetId = $('#edit-asset-id').val();
        if (confirm('Are you sure you want to delete this asset?')) {
            $.ajax({
                url: '/delete_asset',
                type: 'POST',
                data: JSON.stringify({ id: assetId }),
                contentType: 'application/json',
                success: function(response) {
                    alert('Asset deleted successfully!');
                    $('#editAssetModal').modal('hide');
                    location.reload();  // Optionally reload to update the page
                },
                error: function(xhr, status, error) {
                    alert('Error deleting asset.');
                    console.error("Error deleting asset:", error);
                }
            });
        }
    });

    // Saving portfolio value
    function savePortfolioValue() {
        var totalPortfolioValue = $('#portfolio-value').data('total-portfolio-value');

        $.ajax({
            url: '/save_portfolio_value',  // The route to save the portfolio value
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ "current_value": totalPortfolioValue }),
            success: function(response) {
                console.log(response.message);
            },
            error: function(xhr, status, error) {
                console.error("Error saving portfolio value:", error);
            }
        });
    }

    // Save portfolio value on page load
    savePortfolioValue();
});
