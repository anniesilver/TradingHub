import React, { useState } from 'react';
import { Box, IconButton, Tooltip } from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { visuallyHidden } from '@mui/utils';
import { parameterHelp } from '../pages/parameterHelp';

export default function ParameterField({ name, label, children }) {
  const [open, setOpen] = useState(false);
  const help = parameterHelp[name];

  return (
    <Box className="parameter-field" sx={{ display: 'flex', alignItems: 'center', width: '100%', gap: 0.25 }}>
      <Box sx={{ flex: 1, minWidth: 0 }}>{children}</Box>
      <Box component="span" id={`${name}-help`} sx={visuallyHidden}>{help}</Box>
      <Tooltip
        title={help}
        describeChild
        arrow
        open={open}
        onOpen={() => setOpen(true)}
        onClose={() => setOpen(false)}
        enterDelay={150}
      >
        <IconButton
          type="button"
          size="small"
          aria-label={`Help for ${label}`}
          aria-describedby={`${name}-help`}
          onClick={() => setOpen((current) => !current)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') setOpen(false);
          }}
          sx={{ width: 28, height: 32, color: 'text.secondary', flexShrink: 0, '@media (pointer: coarse)': { width: 36, height: 36 } }}
        >
          <HelpOutlineIcon sx={{ fontSize: 16 }} />
        </IconButton>
      </Tooltip>
    </Box>
  );
}
