import React, { useContext, useId, useRef, useState } from 'react';
import { Button, Dialog, DialogContent, DialogTitle, IconButton, Tooltip } from '@mui/material';
import FullscreenRoundedIcon from '@mui/icons-material/FullscreenRounded';
import AppearanceContext from '../AppearanceContext';
import { workspaceCssVariables } from '../themeTokens';

export default function ExpandableChart({ children, title, sample = false }) {
  const [expanded, setExpanded] = useState(false);
  const trigger = useRef(null);
  const closeButton = useRef(null);
  const titleId = useId();
  const { mode } = useContext(AppearanceContext);

  return <div className="expandable-chart">
    <Tooltip title="Expand chart" disableInteractive>
      <IconButton ref={trigger} className="chart-expand-button" size="small" aria-label={`Expand ${title}`} aria-haspopup="dialog" onClick={() => setExpanded(true)}>
        <FullscreenRoundedIcon fontSize="small" />
      </IconButton>
    </Tooltip>
    {!expanded && children}
    <Dialog fullScreen open={expanded} onClose={() => setExpanded(false)} aria-labelledby={titleId}
      className="expanded-chart-dialog" style={workspaceCssVariables(mode)} transitionDuration={0}
      TransitionProps={{ onEntered: () => closeButton.current?.focus(), onExited: () => trigger.current?.focus() }}>
      <DialogTitle id={`${titleId}-header`} component="div" className="expanded-chart-heading">
        <div><h2 id={titleId}>{title}</h2><p>{sample ? 'Fictional sample · UI testing only' : 'Historical simulation · Completed-run values'}</p></div>
        <Button ref={closeButton} autoFocus variant="outlined" onClick={() => setExpanded(false)}>Close chart</Button>
      </DialogTitle>
      <DialogContent className="expanded-chart-content">{expanded && children}</DialogContent>
    </Dialog>
  </div>;
}
