#!/usr/bin/osascript

on run
    set pdfPath to "/Users/jack/Downloads/righttoknowrequestresultsfortieriidataon4southwes/split_pages/page_0001.pdf"
    
    -- Start chonker3
    tell application "Terminal"
        do script "cd /Users/jack/chonker3-new && ./target/release/chonker3"
    end tell
    
    delay 3
    
    -- Focus on chonker3 window
    tell application "System Events"
        -- Wait for window to appear
        repeat 20 times
            if (exists window "CHONKER3 - Sacred Document Chomper" of application process "chonker3") then
                exit repeat
            end if
            delay 0.5
        end repeat
        
        -- Activate the window
        tell process "chonker3"
            set frontmost to true
            delay 1
            
            -- Navigate through UI using Tab key to find Open button
            -- Then press Space to click it
            repeat 20 times
                key code 48 -- Tab key
                delay 0.1
            end repeat
            
            -- Press space to click the Open button
            key code 49 -- Space key
            delay 1
        end tell
        
        -- Now we're in the file dialog
        -- Use Cmd+Shift+G to go to specific path
        keystroke "g" using {command down, shift down}
        delay 0.5
        
        -- Type the file path
        keystroke pdfPath
        delay 0.5
        
        -- Press Enter to go to that location
        key code 36 -- Return key
        delay 1
        
        -- Press Enter again to select the file
        key code 36 -- Return key
        delay 2
        
        -- Now the PDF should be loaded
        -- Tab to the Extract button and press it
        tell process "chonker3"
            -- Tab through UI elements to find Extract button
            repeat 10 times
                key code 48 -- Tab key
                delay 0.1
            end repeat
            
            -- Press space to click Extract
            key code 49 -- Space key
        end tell
        
        -- Wait for extraction to complete
        delay 5
        
        -- Take screenshot
        do shell script "screencapture -x /tmp/chonker3_extracted.png"
        
        -- Close the app
        tell process "chonker3"
            keystroke "q" using command down
        end tell
    end tell
    
    return "Screenshot saved to /tmp/chonker3_extracted.png"
end run