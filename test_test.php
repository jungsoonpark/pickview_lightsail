<?php
// AliExpress API URL for system-level requests
$url = "https://api-sg.aliexpress.com/rest";

// Set your own app_key and app_secret
$appkey = "513774";  // Replace with your actual appkey
$appSecret = "Uzy0PtFg3oqmIFZtXrrGEN9s0speXaXl";  // Replace with your actual appSecret

// Define the API action for generating access token
$action = "/auth/token/create";

// Get the authorization code from the redirect URI after the user authorizes
$authorization_code = "3_513774_b38kGp17gUB9Kq1mFDYfL60v3668";  // Replace with the actual authorization code received

// Initialize IopClient for sending requests
$client = new IopClientImpl($url, $appkey, $appSecret);

// Prepare the request
$request = new IopRequest();
$request->setApiName($action);
$request->addApiParameter("code", $authorization_code);

try {
    // Execute the API request
    $response = $client->execute($request, Protocol::GOP);
    
    // Output the response
    echo json_encode($response);
    echo $response->getGopResponseBody();
} catch (Exception $e) {
    // Handle any exceptions that occur during the API request
    echo $e->getMessage();
}

?>
