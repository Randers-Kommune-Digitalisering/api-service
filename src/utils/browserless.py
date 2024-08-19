import logging
import requests
import json
from requests.auth import HTTPBasicAuth
from .config import BROWSERLESS_CLIENT_ID, BROWSERLESS_CLIENT_SECRET, SD_PERSONALESAG_ROBOT_USERNAME, SD_PERSONALESAG_ROBOT_PASSWORD


def browserless_sd_personalesag_files(input_strings):
    # Input strings should be a list of strings with cpr and employmentidentifier e.g. ['0102039999 01010']
    url = "https://browserless.prototypes.randers.dk/function"
    headers = {
        "Content-Type": "application/javascript",
    }
    data = """
   module.exports = async ({ page }) => {

    // Array of input strings
  const inputStrings = """ + f"{input_strings}" + """

  
 const processRows = async () =>
    {
        await page.waitForTimeout(3000); // Adjust the timeout as necessary
        // Wait for the table wrapper to ensure the table is visible
        await page.waitForSelector('#psagform\\\\:sk\\\\:j_idt107\\\\:0\\\\:j_idt124\\\\:0\\\\:table1\\\\:table1_data', { timeout: 3000 });

        // Extract text from each row
        const rows = await page.evaluate(() => {
            // Get all rows in the table body
            const rows = document.querySelectorAll('#psagform\\\\:sk\\\\:j_idt107\\\\:0\\\\:j_idt124\\\\:0\\\\:table1\\\\:table1_data tr');
            let rowData = [];

            // Iterate through each row
            rows.forEach(row => {
                // Extract text from each cell
                const cells = row.querySelectorAll('td[role="gridcell"]');
                if (cells.length > 0) {
                    // Extract 'Navn' and 'Arkivdato' based on their column positions
                    const navn = cells[3] ? cells[3].innerText.trim() : '';  // Column for 'Navn'
                    const arkivdato = cells[8] ? cells[8].innerText.trim() : '';  // Column for 'Arkivdato'
                    
                    // Add row data
                    rowData.push({ navn, arkivdato });
                }
            });
            console.log("rowData: " + rowData)
            return rowData;
        });
        return rows;
    }

  

  // Function to perform steps for each input string
  const processInputString = async (inputString) => {
    // Wait for the input field to be loaded
    await page.waitForSelector('#tags');

    // Type the text into the input field
    await page.type('#tags', inputString);

    // Wait for the dropdown to appear
try {
    await page.waitForSelector('.ui-menu-item', { visible: true, timeout: 5000 });
} catch (error) {
    console.log("No items found in dropdown menu");
    return; // Exit the function if the dropdown does not appear
}
    // Get all items in the dropdown
const dropdownItems = await page.$$('.ui-menu-item');
if (dropdownItems.length > 0) {
    for (let i = 0; i < dropdownItems.length; i++) {
        const dropdownText = await page.evaluate(el => el.innerText, dropdownItems[i]);
        const dropdownItemSelector = 'li.ui-menu-item:nth-child(' + i+1 + ')';
        await page.waitForTimeout(1500); // Adjust the timeout as necessary
        await page.waitForSelector(dropdownItemSelector); // Ensure the item is visible

        await page.waitForTimeout(1500); // Adjust the timeout as necessary

        // Click the dropdown item using page.evaluate to avoid selection issues
        await page.click(dropdownItemSelector)
        console.log(`Dropdown item ${i + 1} clicked: ${dropdownText}`);
     
        
        // Wait for some time after each click to ensure the page processes it
        await page.waitForTimeout(1500); // Adjust the timeout as necessary
        await page.goto('https://www.silkeborgdata.dk/sdpw/faces/esdh/psag/PersonalesagLoader.xhtml?from=frontpage', {waitUntil: 'networkidle2'});

        // Wait for the specific span element to be loaded
        await page.waitForSelector('#psagform\\\\:sk\\\\:j_idt107\\\\:0\\\\:j_idt124\\\\:0\\\\:j_idt132');

        // Click the element
        await page.click('#psagform\\\\:sk\\\\:j_idt107\\\\:0\\\\:j_idt124\\\\:0\\\\:j_idt132');

        // Wait for rows to be processed
        let rows = await processRows();

        if (rows.length === 1) {
        const [firstItem] = rows;
        if( firstItem.navn === "" && firstItem.arkivdato === "")
        {
            // Wait for rows to be processed
            rows = await processRows();
        } 
        }
        
        // Log the extracted rows
        console.log('Extracted Rows:', rows);

        // Store the results
        allResults.push({ inputString, dropdownText, result: rows });
    }
} else {
    console.log("No dropdown item found.");
}
  };

  // Perform initial login and navigation steps
  await page.goto('https://sd.dk/start',{waitUntil: 'networkidle2' });

  // Log in console when loaded
  console.log("Page loaded");

  // Wait for the button to be available
  await page.waitForSelector('#arbejdspladsButton', { timeout: 5000 });
  console.log("arbejdspladsButton found");

  // Click the button with the id "arbejdspladsButton"
  await page.click('#arbejdspladsButton');
  console.log("Button clicked and navigation completed");

  // Wait for the iframe to be loaded
  await page.waitForSelector('iframe');  // Adjust the selector to target the specific iframe if necessary

  // Get the iframe element
  const iframeElement = await page.$('iframe');  // Adjust the selector to target the specific iframe if necessary
  const iframe = await iframeElement.contentFrame();

  // Wait for the select element to be loaded inside the iframe
  await iframe.waitForSelector('#oiosaml-idp');

  // Get the value of the option with text 'Randers Kommune' inside the iframe
  const value = await iframe.evaluate(() => {
      const options = document.querySelectorAll('#oiosaml-idp option');
      for (const option of options) {
          if (option.textContent.trim() === 'Randers Kommune') {
              return option.value;
          }
      }
      return null;
  });

  // Print the value
  console.log(value);

  await page.goto("https://sd.dk/" + value);
  
  // Log a message indicating the button was clicked
  console.log("Button clicked and navigation completed");

  // Wait for the username input field to be available
  await page.waitForSelector('#userNameInput');

  // Type the username
  await page.type('#userNameInput', 'laksen04\\\DQ99999');

  // Wait for the password input field to be available
  await page.waitForSelector('#passwordInput');

  // Type the password
  await page.type('#passwordInput', 'De3smaagrise!'); 

  // Click the submit button
  await page.click('#submitButton');

  // Log a message indicating the login was attempted
  console.log("Login attempted");

  // Wait for some time after selection
  await page.waitForTimeout(1500); // Adjust the timeout as necessary

  // Wait for the username input field to be available
  await page.waitForSelector('#product-cf662da2-9d3c-0108-e043-0a10f6400108');
  await page.goto('https://www.silkeborgdata.dk/sdpw/' ,{waitUntil: 'networkidle2' });

  // Store the results for each input string
  let allResults = [];

  for (let inputString of inputStrings) {
    await processInputString(inputString);
    //await page.goto('https://www.silkeborgdata.dk/sdpw/' ,{waitUntil: 'networkidle2' });
  }
  // Close the page
  //await page.close();
    return {
        data: {
        allResults
        },
        type: 'application/json'
    };

};
    """

    response = requests.post(url, headers=headers, data=data, auth=HTTPBasicAuth(username=BROWSERLESS_CLIENT_ID,
                                                                                 password=BROWSERLESS_CLIENT_SECRET))
    return response
